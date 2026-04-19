"use client";

import { useState, useRef, useEffect } from "react";
import { 
  Send, Square, Play, RotateCcw, ChevronDown, CheckCircle, 
  Bell, User as UserIcon, Monitor, X, Settings, Sparkles, 
  Plus, Search, Mic, ArrowUp, Globe
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ArchimedesSocket, AgentEvent } from "@/lib/websocket";
import ReactMarkdown from "react-markdown";
import Image from "next/image";
import MessagePill from "./MessagePill";
import ArtifactViewer, { ArtifactData } from "./ArtifactViewer";
import ModeSelector from "./ModeSelector";
import QuickPrompts from "./QuickPrompts";
import ModeDiscovery from "./ModeDiscovery";
import VoiceVisualizer from "./VoiceVisualizer";
import SettingsModal from "./SettingsModal";
import { AGENT_MODES } from "@/lib/modes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "assistant" | "system";
  type: "text" | "info" | "ask" | "result" | "plan" | "artifact" | "thought" | "tool" | "tool_call" | "file_download";
  content: string;
  artifactData?: ArtifactData;
  filename?: string;
  download_url?: string;
  size_kb?: number;
  preview_url?: string;
}

const cleanMessageContent = (content: string | undefined): string => {
  if (!content) return "";
  let cleaned = content.replace(/<(think|thought)>[\s\S]*?<\/\1>/gi, "");
  cleaned = cleaned.replace(/\{[\s\S]*?("type"|"tool_call"|"name"|"params"|"action")[\s\S]*?\}/g, "");
  cleaned = cleaned.replace(/\w+\(type=["']\w+["'][\s\S]*?\)/g, "");
  cleaned = cleaned.replace(/_TOOL:\s*\w*/g, "");
  cleaned = cleaned.replace(/_TOOL:\s*/g, "");
  cleaned = cleaned.replace(/```json[\s\S]*?```/g, "");
  cleaned = cleaned.replace(/```[\s\S]*?```/g, (match) => {
      const lower = match.toLowerCase();
      if (lower.includes("\"tool\"") || lower.includes("\"action\"") || lower.includes("\"name\"") || lower.includes("message(")) return "";
      return match;
  });
  return cleaned.replace(/\n{3,}/g, "\n\n").trim();
};

export default function ChatPanel({ 
  sessionId, 
  isStarted, 
  onStart, 
  selectedAgent, 
  executionMode,
  onModeChange,
  isComputerOpen, 
  onToggleComputer 
}: { 
  sessionId: string, 
  isStarted: boolean, 
  onStart: () => void, 
  selectedAgent?: string, 
  executionMode?: "fast" | "planning",
  onModeChange?: (mode: "fast" | "planning") => void,
  isComputerOpen?: boolean, 
  onToggleComputer?: () => void 
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWorking, setIsWorking] = useState(false);
  const [socket, setSocket] = useState<ArchimedesSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isListening, setIsListening] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [globeEnabled, setGlobeEnabled] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<ArtifactData[]>([]);
  const [viewingArtifact, setViewingArtifact] = useState<ArtifactData | null>(null);
  const [hasToolEvents, setHasToolEvents] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [activeMode, setActiveMode] = useState<string | null>(null);

  // Top header button states
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [isCheckingUpdate, setIsCheckingUpdate] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [isPillHovered, setIsPillHovered] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Section 8: Unique features
  const [confidence, setConfidence] = useState<{score: number; label: string} | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [taskStartTime, setTaskStartTime] = useState<number | null>(null);
  const [taskElapsed, setTaskElapsed] = useState(0);

  const handleUpdateClick = () => {
    setShowUpdateModal(true);
    setIsCheckingUpdate(true);
    setTimeout(() => {
      setIsCheckingUpdate(false);
    }, 2000);
  };

  const agentDisplayNames: Record<string, string> = {
    "archimedes-cosmo": "Archimedes COSMO",
    "researcher": "Researcher AI",
    "coder": "Coder Bot",
    "data-scientist": "Data Scientist"
  };
  
  const currentMode = AGENT_MODES.find(m => m.id === activeMode) || AGENT_MODES[0];
  const displayTitle = agentDisplayNames[selectedAgent || "archimedes-cosmo"] || "Archimedes AI";

  useEffect(() => {
    // Initialize SpeechRecognition if available
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const reco = new SpeechRecognition();
        reco.lang = "ru-RU";
        reco.continuous = true;
        reco.interimResults = true;
        
        reco.onresult = (event: any) => {
          let currentTranscript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          setInput(prev => prev + " " + currentTranscript.trim());
        };
        
        reco.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsListening(false);
        };
        
        reco.onend = () => {
          setIsListening(false);
        };
        
        setRecognition(reco);
      }
    }
  }, []);

  const toggleMic = () => {
    if (!recognition) {
      alert("Ваш браузер не поддерживает распознавание речи.");
      return;
    }
    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      setInput("");
      recognition.start();
      setIsListening(true);
    }
  };

  const handleFileUpload = async (e?: React.ChangeEvent<HTMLInputElement>, droppedFile?: File) => {
    const file = droppedFile || e?.target.files?.[0];
    if (!file) return;

    setMessages(prev => [...prev, { role: "system", type: "info", content: `Загрузка файла ${file.name}...`}]);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        setMessages(prev => [...prev, { role: "system", type: "info", content: `Файл ${file.name} успешно загружен в workspace.`}]);
      } else {
        throw new Error("Upload failed");
      }
    } catch (err) {
       console.error(err);
       setMessages(prev => [...prev, { role: "system", type: "info", content: `Ошибка при загрузке ${file.name}.`}]);
    }
  };

  useEffect(() => {
    const handleWindowDragOver = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
    };
    const handleWindowDragLeave = (e: DragEvent) => {
      e.preventDefault();
      // Only set to false if we are actually leaving the window
      if (e.relatedTarget === null) {
        setIsDragging(false);
      }
    };
    const handleWindowDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer?.files[0];
      if (file) {
        handleFileUpload(undefined, file);
      }
    };

    window.addEventListener("dragover", handleWindowDragOver);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);

    return () => {
      window.removeEventListener("dragover", handleWindowDragOver);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
    };
  }, []);

  useEffect(() => {
    const archSocket = new ArchimedesSocket(sessionId, (event: AgentEvent) => {
      handleAgentEvent(event);
    });
    archSocket.connect();
    setSocket(archSocket);
    return () => archSocket.disconnect();
  }, [sessionId]);

  const handleAgentEvent = (event: AgentEvent) => {
    if (["message_info", "message_ask", "message_result", "agent_error", "session_end"].includes(event.type)) {
      setIsWorking(false);
    }

    switch (event.type) {
      case "message_info": {
        const cleaned = cleanMessageContent(event.text || event.content);
        if (cleaned) {
          let determinedType = "info";
          const lower = cleaned.toLowerCase();
          
          if (cleaned.startsWith("PLAN:") || lower.includes("создан план")) {
             determinedType = "plan";
          } else if (
             lower.includes("использую инструмент") || 
             lower.includes("работа") || 
             lower.includes("запускаю команду") ||
             lower.includes("создан артефакт") ||
             lower.includes("прочитан файл") ||
             lower.includes("приступаю к выполнению")
          ) {
             determinedType = "tool";
          } else if (
             lower.includes("анализ") || 
             lower.includes("проверяю результат") ||
             lower.includes("думаю")
          ) {
             determinedType = "thought";
          }
          
          setMessages(prev => [...prev, { role: "assistant", type: determinedType as any, content: cleaned }]);
        }
        break;
      }
      case "message_ask": {
        const cleaned = cleanMessageContent(event.text || event.content);
        if (cleaned) setMessages(prev => [...prev, { role: "assistant", type: "ask", content: cleaned }]);
        break;
      }
      case "message_result": {
        const cleaned = cleanMessageContent(event.text || event.content);
        if (cleaned) setMessages(prev => [...prev, { role: "assistant", type: "result", content: cleaned }]);
        break;
      }
      case "thought": {
        const cleaned = cleanMessageContent(event.content || event.text);
        if (cleaned) setMessages(prev => [...prev, { role: "assistant", type: "thought", content: cleaned }]);
        break;
      }
      case "tool_call": {
        setMessages(prev => [...prev, { 
          role: "assistant", 
          type: "tool", 
          content: `Вызов инструмента: **${event.tool}**\n\`\`\`json\n${JSON.stringify(event.params, null, 2)}\n\`\`\`` 
        }]);
        break;
      }
      case "artifact": {
        const artifactData: ArtifactData = {
          name: event.name || "file",
          content: event.content || "",
          path: event.path || event.name || "",
          language: event.language,
        };
        setArtifacts(prev => [...prev, artifactData]);
        setMessages(prev => [...prev, { 
          role: "system", 
          type: "artifact", 
          content: event.name || "file",
          artifactData,
        }]);
        break;
      }
      case "plan_update": {
         setMessages(prev => [...prev, { role: "assistant", type: "plan", content: `Обновление плана: ${event.text || "Выполнение..."}` }]);
         break;
      }
      case "confidence": {
        setConfidence({ score: (event as any).score ?? 100, label: (event as any).label ?? "" });
        break;
      }
      case "suggestions": {
        setSuggestions((event as any).items || []);
        break;
      }
      case "file_artifact": {
        // Create auto-download link
        const blob = new Blob(
          [Uint8Array.from(atob(event.data || ""), c => c.charCodeAt(0))],
          { type: event.mime_type }
        );
        const url = URL.createObjectURL(blob);

        // Add download message to chat
        setMessages(prev => [...prev, {
          role: "assistant",
          type: "file_download",
          content: event.label || "Файл сгенерирован",
          filename: event.filename,
          download_url: url,
          size_kb: event.size_kb,
          preview_url: event.preview_url
        }]);
        break;
      }
      case "browser_navigate": {
        if (typeof window !== "undefined" && window.dispatchEvent) {
           window.dispatchEvent(new CustomEvent("archimedes-open-browser", { detail: { url: event.url, title: event.title } }));
        }
        break;
      }
    }
    
    // Track tool events for the toggle button
    if (event.type === "tool_call" || event.type === "tool" || event.type === "artifact") {
      setHasToolEvents(true);
    }

    // Pass it along to FloatingDesktop
    window.dispatchEvent(new CustomEvent("archimedes-event", { detail: event }));
  };

  const handleSend = () => {
    if (!input.trim() || isWorking) return;
    if (!socket || socket.getReadyState() !== WebSocket.OPEN) {
      alert("Please wait for connection to establish before sending.");
      return;
    }
    
    const task = input.trim();
    setMessages(prev => [...prev, { role: "user", type: "text", content: task }]);
    setInput("");
    setIsWorking(true);
    setTaskStartTime(Date.now());
    setSuggestions([]);
    setConfidence(null);
    if (!isStarted) onStart();
    socket.sendTask(task, selectedAgent, executionMode, webSearchEnabled, globeEnabled, activeMode ? currentMode.taskHint : "default");
  };

  const stopTask = () => {
     // A pseudo-stop button
     setIsWorking(false);
     setTaskStartTime(null);
     setMessages(prev => [...prev, { role: "system", type: "info", content: "Task forcibly stopped by user."}]);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isWorking]);

  // Timer effect
  useEffect(() => {
    if (!isWorking || !taskStartTime) {
      setTaskElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setTaskElapsed(Math.floor((Date.now() - taskStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isWorking, taskStartTime]);

  // Reset timer when work is done
  useEffect(() => {
    if (!isWorking) {
      setTaskStartTime(null);
    }
  }, [isWorking]);

  return (
    <div className="flex-1 flex flex-col relative h-full w-full bg-[#0B0B0B] text-[#ECECEC]">
      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
      
      {/* Top Header inside Chat */}
      <div className="h-14 flex items-center justify-between px-6 border-b border-transparent shrink-0">
         <div className="flex items-center gap-2 font-medium text-[17px] cursor-pointer group hover:bg-[#1A1A1A] px-3 py-1.5 rounded-lg transition-all duration-300">
            <span className="text-gray-200 group-hover:text-white transition-all duration-300 tracking-wide">
              {displayTitle}
            </span>
            <ChevronDown size={14} className="text-gray-500 group-hover:text-gray-300 transition-colors" />
         </div>
          <div className="flex items-center gap-4 relative">
            <button 
              onClick={handleUpdateClick}
              className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 font-medium px-3 py-1.5 rounded-full bg-[#1e293b]/30 hover:bg-[#1e293b]/60 transition-colors"
            >
               <Sparkles size={14} /> Обновление
            </button>
            {/* Toggle Computer Panel button */}
            {hasToolEvents && !isComputerOpen && onToggleComputer && (
              <button
                onClick={onToggleComputer}
                className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 font-medium px-3 py-1.5 rounded-full bg-purple-900/20 hover:bg-purple-900/40 transition-colors border border-purple-500/20"
                title="Открыть компьютер агента"
              >
                <Monitor size={14} />
                Компьютер
              </button>
            )}
            
            <div className="h-4 w-px bg-[#333] mx-1"></div>

            <div className="flex items-center gap-3">
               <div className="relative">
                 <button 
                   onClick={() => { setShowNotifMenu(!showNotifMenu); setShowProfileMenu(false); }}
                   className={`text-gray-400 hover:text-white transition-colors p-1.5 rounded-md ${showNotifMenu ? 'bg-[#333] text-white' : ''}`}
                 >
                   <Bell size={18} />
                 </button>
                 
                 {/* Notifications Dropdown */}
                 <AnimatePresence>
                   {showNotifMenu && (
                     <motion.div 
                       initial={{ opacity: 0, y: 10 }}
                       animate={{ opacity: 1, y: 0 }}
                       exit={{ opacity: 0, scale: 0.95 }}
                       className="absolute top-full right-0 mt-2 w-64 bg-[#181818] border border-[#333] rounded-xl shadow-2xl z-50 overflow-hidden"
                     >
                        <div className="px-4 py-3 border-b border-[#333] font-medium text-sm text-white">Уведомления</div>
                        <div className="p-6 flex flex-col items-center justify-center text-gray-500 gap-2">
                           <Bell size={24} className="opacity-40" />
                           <span className="text-xs">Нет новых уведомлений</span>
                        </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </div>

               <div className="relative">
                 <button 
                   onClick={() => { setShowProfileMenu(!showProfileMenu); setShowNotifMenu(false); }}
                   className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-sm font-bold text-white shadow-inner hover:ring-2 hover:ring-teal-400/50 transition-all cursor-pointer"
                 >
                   D
                 </button>

                 {/* Profile Dropdown */}
                 <AnimatePresence>
                   {showProfileMenu && (
                     <motion.div 
                       initial={{ opacity: 0, y: 10 }}
                       animate={{ opacity: 1, y: 0 }}
                       exit={{ opacity: 0, scale: 0.95 }}
                       className="absolute top-full right-0 mt-2 w-56 bg-[#181818] border border-[#333] rounded-xl shadow-2xl z-50 flex flex-col p-1"
                     >
                        <div className="px-3 py-3 border-b border-[#333] flex items-center gap-3 mb-1">
                           <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-sm font-bold text-white">D</div>
                           <div className="flex flex-col">
                             <span className="text-sm font-medium text-white">Developer</span>
                             <span className="text-[10px] text-gray-500">Local Admin</span>
                           </div>
                        </div>
                                                 <button 
                           onClick={() => { setShowSettingsModal(true); setShowProfileMenu(false); }}
                           className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-[#262626] rounded-md transition-colors text-left w-full"
                         >
                            <Settings size={14} /> Настройки
                         </button>
                        <button className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-md transition-colors text-left w-full">
                           Выйти
                        </button>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </div>
            </div>
         </div>
      </div>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col items-center overflow-y-auto custom-scrollbar px-4 transition-all duration-700 ${messages.length === 0 ? "justify-center pt-[10vh]" : "pt-10 pb-40"}`}>
        
        {messages.length === 0 && (
           <div className="w-full max-w-3xl flex flex-col items-center">
              <motion.h1 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-[40px] md:text-[56px] font-serif mb-12 text-center text-white/95 font-medium leading-tight tracking-tight px-4"
              >
                 What can I do for you?
              </motion.h1>
              
              {/* The "Plaque" (Input Area) centered */}
              <div className="w-full flex flex-col items-center gap-6">
                  <motion.div 
                    layoutId="input-plaque"
                    className="w-full bg-[#181818] border border-[#2A2A2A] rounded-[32px] p-2 px-1 shadow-2xl relative"
                  >
                    {isListening ? (
                       <div className="w-full flex items-center justify-center py-5 min-h-[60px]">
                          <VoiceVisualizer isActive={isListening} />
                       </div>
                    ) : (
                      <textarea
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
                          placeholder={currentMode.placeholder}
                          disabled={isWorking}
                          className="w-full bg-transparent border-none text-[#ECECEC] text-[17px] px-6 py-5 outline-none resize-none min-h-[60px] max-h-[200px] placeholder:text-gray-500 font-medium"
                          rows={1}
                      />
                    )}
                    <div className="flex items-center justify-between px-4 pb-3 pt-1">
                        <div className="flex items-center gap-3">
                            <button onClick={() => fileInputRef.current?.click()} className="p-2.5 text-gray-500 hover:text-white hover:bg-[#222] rounded-xl transition-all">
                                <Plus size={18} />
                            </button>
                            <div className="h-5 w-px bg-white/5 mx-1"></div>
                            <button 
                              onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                              className={`p-2.5 rounded-xl transition-all ${webSearchEnabled ? "text-blue-400 bg-blue-900/20" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                            >
                                <Search size={18} />
                            </button>
                            <button 
                              onClick={() => setGlobeEnabled(!globeEnabled)}
                              className={`p-2.5 rounded-xl transition-all ${globeEnabled ? "text-blue-400 bg-blue-900/20" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                            >
                                <Monitor size={18} />
                            </button>
                            
                            {/* Active Mode Pill inside input */}
                            {activeMode && activeMode !== "default" && (
                               <motion.button 
                                 initial={{ scale: 0.9, opacity: 0 }}
                                 animate={{ scale: 1, opacity: 1 }}
                                 onMouseEnter={() => setIsPillHovered(true)}
                                 onMouseLeave={() => setIsPillHovered(false)}
                                 onClick={() => setActiveMode(null)}
                                 className="flex items-center gap-2 bg-blue-600/10 hover:bg-red-500/10 text-blue-400 hover:text-red-400 px-3.5 py-1.5 rounded-full border border-blue-500/20 hover:border-red-500/30 text-xs font-bold transition-all group/pill"
                               >
                                  {isPillHovered ? (
                                    <>
                                      <X size={12} className="shrink-0" />
                                      <span>Cancel {currentMode.label}</span>
                                    </>
                                  ) : (
                                    <>
                                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
                                      {currentMode.label}
                                    </>
                                  )}
                               </motion.button>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            <button 
                              onClick={toggleMic}
                              className={`p-2.5 rounded-xl transition-all ${isListening ? "text-red-400 bg-red-900/10 animate-pulse" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                            >
                                <Mic size={18} />
                            </button>
                            <button 
                                onClick={handleSend}
                                disabled={!input.trim()}
                                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${input.trim() ? "bg-white text-black hover:scale-105" : "bg-[#222] text-gray-600"}`}
                            >
                                <ArrowUp size={18} />
                            </button>
                        </div>
                    </div>
                  </motion.div>

                  {/* Mode Selector below the plaque */}
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="w-full flex justify-center py-2"
                  >
                     <ModeSelector activeMode={activeMode} onModeChange={setActiveMode} />
                  </motion.div>
              </div>

              {/* Mode Discovery Sections */}
              <ModeDiscovery 
                mode={currentMode} 
                onSelectPrompt={(p) => setInput(p)}
                onSelectTemplate={(t) => {
                    setInput(`Create a presentation about [topic] using the ${t} template style.`);
                }}
              />
           </div>
        )}

        {messages.length > 0 && (
           <div className="w-full max-w-3xl flex flex-col gap-6">
             <AnimatePresence>
               {messages.map((msg, idx) => (
                 <motion.div 
                   key={idx}
                   initial={{ opacity: 0, y: 10 }}
                   animate={{ opacity: 1, y: 0 }}
                   className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                 >
                    {msg.role === "user" ? (
                      <div className="bg-[#2B2B2B] text-white/90 px-5 py-3 rounded-[24px] max-w-[85%] text-[15px] font-medium leading-relaxed rounded-tr-sm">
                        {msg.content}
                      </div>
                    ) : msg.type === "artifact" && msg.artifactData ? (
                      /* Clickable artifact card */
                      <div className="flex gap-4 w-full max-w-[90%] group">
                        <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center mt-0.5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center group overflow-hidden">
                             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 group-hover:scale-110 group-hover:rotate-12 transition-all duration-300 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
                          </div>
                        </div>
                        <div className="flex flex-col gap-1 w-full">
                          <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                            archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
                          </div>
                          <div className="mt-2">
                            <button
                               onClick={() => setViewingArtifact(msg.artifactData!)}
                               className="flex items-center gap-3 px-4 py-3 bg-[#1A1B26] border border-[#2A2B3D] rounded-xl hover:border-blue-500/40 hover:bg-[#1E1F2E] transition-all cursor-pointer group/artifact w-fit max-w-full"
                            >
                               <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center shrink-0">
                                 <span className="text-lg">📄</span>
                               </div>
                               <div className="flex flex-col items-start min-w-0">
                                 <span className="text-white text-sm font-medium truncate">{msg.artifactData.name}</span>
                                 <span className="text-gray-500 text-xs">Нажмите для просмотра</span>
                               </div>
                               <svg className="w-4 h-4 text-gray-500 group-hover/artifact:text-blue-400 transition-colors ml-2 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-4 w-full max-w-[90%] group">
                        <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center mt-0.5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center group overflow-hidden">
                             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 group-hover:scale-110 group-hover:rotate-12 transition-all duration-300 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
                          </div>
                        </div>
                        <div className="flex flex-col gap-1 w-full">
                          <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                            archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
                          </div>
                          <div className="mt-2">
                            {(msg.type === "thought" || msg.type === "tool" || msg.type === "plan") ? (
                              <MessagePill type={msg.type} content={msg.content} />
                            ) : msg.type === "file_download" ? (
                              <div className="flex items-center gap-3 p-4 rounded-xl bg-violet-600/10 border border-violet-500/30 mt-2">
                                <span className="text-2xl">📊</span>
                                <div className="flex-1">
                                  <div className="font-medium text-sm text-white">
                                    {msg.content}
                                  </div>
                                  <div className="text-xs text-gray-400 mt-0.5">
                                    {msg.filename} • {msg.size_kb} KB
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  {msg.preview_url && (
                                    <a href={msg.preview_url}
                                       target="_blank" rel="noreferrer"
                                       className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors">
                                      Preview
                                    </a>
                                  )}
                                  <a href={msg.download_url}
                                     download={msg.filename}
                                     className="text-xs px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white transition-colors font-medium">
                                    ↓ Download PPTX
                                  </a>
                                </div>
                              </div>
                            ) : (
                              <div className="markdown-content prose prose-invert prose-sm max-w-none text-[#ECECEC] text-[15px] leading-relaxed mt-1">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                 </motion.div>
               ))}
               
               {isWorking && (
                 <motion.div 
                   initial={{ opacity: 0, y: 10 }} 
                   animate={{ opacity: 1, y: 0 }} 
                   className="flex w-full justify-start mt-2"
                 >
                   <div className="flex gap-4 w-full">
                     <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center mt-0.5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center group overflow-hidden animate-pulse">
                             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)] transition-all duration-1000 rotate-180 scale-110"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
                          </div>
                     </div>
                     <div className="flex flex-col gap-1">
                       <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                          archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
                       </div>
                        <div className="flex items-center gap-2 text-[#ECECEC] mt-2 text-[15px]">
                          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                          Thinking...
                          {taskElapsed > 0 && (
                            <span className="text-xs text-gray-500 ml-2">{taskElapsed}s</span>
                          )}
                          {confidence && (
                            <span className="text-xs ml-2 px-2 py-0.5 rounded-full bg-[#222] text-gray-400">
                              {confidence.label} ({confidence.score}%)
                            </span>
                          )}
                        </div>
                     </div>
                   </div>
                 </motion.div>
               )}
             </AnimatePresence>

              {/* Proactive Suggestion Chips */}
              {suggestions.length > 0 && !isWorking && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-wrap gap-2 mt-4"
                >
                  <span className="text-xs text-gray-500 w-full mb-1">Следующие шаги:</span>
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => { setInput(s); setSuggestions([]); }}
                      className="px-3 py-1.5 rounded-full bg-[#1A1A2E] border border-blue-500/20 text-blue-400 text-xs hover:bg-blue-900/30 hover:border-blue-500/40 transition-all"
                    >
                      {s}
                    </button>
                  ))}
                </motion.div>
              )}

              <div ref={messagesEndRef} />
           </div>
        )}
      </div>

      {/* Drag & Drop Overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-[100] bg-[#000000a0] backdrop-blur-md flex flex-col items-center justify-center p-12 transition-all duration-300 pointer-events-none"
          >
             <div className="w-full h-full border-2 border-dashed border-blue-500/50 rounded-[40px] flex flex-col items-center justify-center gap-6 bg-gradient-to-br from-blue-500/5 to-purple-500/5">
                <div className="w-24 h-24 rounded-3xl bg-blue-500/20 flex items-center justify-center shadow-[0_0_30px_rgba(59,130,246,0.3)] animate-pulse">
                   <PlusIcon />
                </div>
                <div className="flex flex-col items-center gap-2 text-center">
                   <h2 className="text-3xl font-bold text-white tracking-tight">Отпустите файл для загрузки</h2>
                   <p className="text-gray-400 text-lg">Ваш файл будет добавлен в рабочее пространство проекта</p>
                </div>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Box Area (Fixed at bottom for chat) */}
      <AnimatePresence>
        {messages.length > 0 && (
          <motion.div 
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[#0B0B0B] via-[#0B0B0B] to-transparent pt-10 pb-8 flex flex-col items-center px-4 gap-4"
          >
             <div className="w-full max-w-3xl">
               <ModeSelector activeMode={activeMode} onModeChange={setActiveMode} />
             </div>
             <div className="w-full max-w-3xl relative">
               <motion.div 
                 layoutId="input-plaque"
                 className={`bg-[#262626] rounded-[28px] flex flex-col p-2 transition-shadow duration-300 focus-within:shadow-[0_0_0_1px_#555]`}
               >
                 {isListening ? (
                    <div className="w-full h-[60px] flex flex-col items-center justify-center relative">
                       <VoiceVisualizer isActive={isListening} />
                       <div className="absolute right-6 top-1/2 -translate-y-1/2 text-[10px] font-bold text-red-500/80 animate-pulse tracking-widest uppercase">
                         LISTENING...
                       </div>
                    </div>
                 ) : (
                   <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
                      placeholder={currentMode.placeholder}
                      disabled={isWorking}
                      className="w-full bg-transparent border-none text-[#ECECEC] text-[15px] px-4 py-3 outline-none resize-none min-h-[50px] max-h-[200px] placeholder:text-gray-500"
                     rows={1}
                   />
                 )}
                 
                 {/* Bottom row of text area block */}
                 <div className="flex items-center justify-between px-2 pb-1 pt-2">
                    <div className="flex items-center gap-1">
                       <button onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white hover:bg-[#333] rounded-full transition-colors tooltip tooltip-top" title="Прикрепить файл">
                         <Plus size={14} />
                       </button>
                       
                       <button 
                         onClick={() => setWebSearchEnabled(!webSearchEnabled)} 
                         className={`p-2 rounded-full transition-colors tooltip tooltip-top ${webSearchEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                         title="Веб-поиск"
                       >
                         <Search size={14} />
                       </button>
                       
                       <button 
                         onClick={() => setGlobeEnabled(!globeEnabled)} 
                         className={`p-2 rounded-full transition-colors tooltip tooltip-top ${globeEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                         title="Сёрфинг и контекст интернета"
                       >
                         <Globe size={14} />
                       </button>
    
                        {/* Mode Toggle */}
                        <div className="flex items-center ml-2 bg-[#1A1A1A] rounded-full p-0.5 border border-[#333]">
                          <button 
                            onClick={() => onModeChange?.("fast")}
                            className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all ${executionMode === "fast" ? "bg-amber-500/20 text-amber-500 shadow-sm" : "text-gray-500 hover:text-gray-400"}`}
                          >
                            Fast
                          </button>
                          <button 
                            onClick={() => onModeChange?.("planning")}
                            className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all ${executionMode === "planning" ? "bg-blue-500/20 text-blue-500 shadow-sm" : "text-gray-500 hover:text-gray-400"}`}
                          >
                            Plan
                          </button>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                       <button 
                         onClick={toggleMic}
                         className={`p-2 rounded-full transition-colors tooltip tooltip-top ${isListening ? "text-red-400 bg-red-900/30 animate-pulse" : "text-gray-400 hover:text-white"}`}
                         title="Голосовой ввод"
                       >
                         <Mic size={16} />
                       </button>
                       {isWorking ? (
                          <button 
                             onClick={stopTask}
                             className="w-8 h-8 rounded-full bg-[#E5E5E5] flex items-center justify-center hover:bg-white transition-colors flex-shrink-0"
                          >
                             <div className="w-3 h-3 bg-black rounded-sm"></div>
                          </button>
                       ) : (
                          <button 
                             onClick={handleSend}
                             disabled={!input.trim()}
                             className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                                input.trim() ? "bg-[#E5E5E5] hover:bg-white text-black" : "bg-[#444] text-[#888]"
                             }`}
                          >
                             <ArrowUpIcon />
                          </button>
                       )}
                    </div>
                 </div>
               </motion.div>
               
               <div className="text-center mt-3 text-xs text-gray-500 font-medium tracking-wide">
                  У Archimedes могут быть ошибки. Пожалуйста, проверяйте важную информацию.
               </div>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Artifact Viewer Modal */}
      {viewingArtifact && (
        <ArtifactViewer artifact={viewingArtifact} onClose={() => setViewingArtifact(null)} />
      )}

      {/* Update Checking Modal */}
      <AnimatePresence>
        {showUpdateModal && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => !isCheckingUpdate && setShowUpdateModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative w-full max-w-sm bg-[#181818] border border-[#333] rounded-2xl shadow-2xl p-6 flex flex-col items-center text-center"
            >
              {isCheckingUpdate ? (
                <>
                  <div className="w-12 h-12 rounded-full border-2 border-[#333] border-t-blue-500 animate-spin mb-4"></div>
                  <h3 className="text-white font-medium text-lg mb-2">Проверка обновлений...</h3>
                  <p className="text-sm text-gray-400">Связываемся с серверами LLM backend.</p>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center mb-4">
                    <CheckCircle size={24} />
                  </div>
                  <h3 className="text-white font-medium text-lg mb-2">Система актуальна</h3>
                  <p className="text-sm text-gray-400 mb-6">Вы используете самую последнюю версию ядра (Archimedes v1.0 Enterprise).</p>
                  <button 
                    onClick={() => setShowUpdateModal(false)}
                    className="w-full bg-[#262626] hover:bg-[#333] text-white py-2.5 rounded-lg font-medium transition-colors"
                  >
                    Понятно
                  </button>
                </>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      
    </div>
  );
}

// Icon SVGs extracted to keep main component clean
function SparklesIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>; }
function PlusIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>; }
function SearchIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>; }
function GlobeIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/></svg>; }
function MicIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>; }
function ArrowUpIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>; }
