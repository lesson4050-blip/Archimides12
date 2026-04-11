"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Square, Play, RotateCcw, ChevronDown, CheckCircle, Bell, User as UserIcon, Monitor } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ArchimedesSocket, AgentEvent } from "@/lib/websocket";
import ReactMarkdown from "react-markdown";
import Image from "next/image";
import MessagePill from "./MessagePill";
import ArtifactViewer, { ArtifactData } from "./ArtifactViewer";

interface Message {
  role: "user" | "assistant" | "system";
  type: "text" | "info" | "ask" | "result" | "plan" | "artifact";
  content: string;
  artifactData?: ArtifactData;
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setMessages(prev => [...prev, { role: "system", type: "info", content: `Загрузка файла ${file.name}...`}]);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/v1/upload", {
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
    if (!isStarted) onStart();
    socket.sendTask(task, selectedAgent, executionMode);
  };

  const stopTask = () => {
     // A pseudo-stop button
     setIsWorking(false);
     setMessages(prev => [...prev, { role: "system", type: "info", content: "Task forcibly stopped by user."}]);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isWorking]);

  return (
    <div className="flex-1 flex flex-col relative h-full w-full bg-[#0B0B0B] text-[#ECECEC]">
      
      {/* Top Header inside Chat */}
      <div className="h-14 flex items-center justify-between px-6 border-b border-transparent shrink-0">
         <div className="flex items-center gap-2 font-medium text-lg cursor-pointer hover:bg-[#1A1A1A] px-3 py-1.5 rounded-lg transition-colors">
            Archimedes 1.0 Lite <ChevronDown size={14} className="text-gray-400" />
         </div>
         <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 font-medium px-3 py-1.5 rounded-full bg-[#1e293b]/30">
               <SparklesIcon /> Обновление
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
            <div className="flex items-center gap-3">
               <button className="text-gray-400 hover:text-white"><Bell size={18} /></button>
               <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-sm font-bold text-white shadow-inner">
                 D
               </div>
            </div>
         </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col items-center overflow-y-auto custom-scrollbar px-4 pt-10 pb-40">
        
        {!isStarted && messages.length === 0 ? (
           <div className="w-full max-w-3xl flex flex-col items-center justify-center pt-[15vh]">
              <h1 className="text-[40px] md:text-[48px] font-serif mb-12 text-center text-white/95 font-medium leading-tight tracking-tight">
                 Что я могу сделать для вас?
              </h1>
           </div>
        ) : (
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
                          <Image src="/logo-optimized.png" alt="Archimedes Logo" width={32} height={32} className="object-contain" />
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
                          <Image src="/logo-optimized.png" alt="Archimedes Logo" width={32} height={32} className="object-contain" />
                        </div>
                        <div className="flex flex-col gap-1 w-full">
                          <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                            archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
                          </div>
                          <div className="mt-2">
                            {(msg.type === "thought" || msg.type === "tool" || msg.type === "plan") ? (
                              <MessagePill type={msg.type} content={msg.content} />
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
                        <Image src="/logo-optimized.png" alt="Archimedes Logo" width={32} height={32} className="object-contain" />
                     </div>
                     <div className="flex flex-col gap-1">
                       <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                          archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
                       </div>
                       <div className="flex items-center gap-2 text-[#ECECEC] mt-2 text-[15px]">
                         <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                         Thinking...
                       </div>
                     </div>
                   </div>
                 </motion.div>
               )}
             </AnimatePresence>
             <div ref={messagesEndRef} />
           </div>
        )}
      </div>

      {/* Floating Task Progress Bar */}
      <AnimatePresence>
        {isWorking && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-[140px] left-1/2 -translate-x-1/2 bg-[#2D2D2D] border border-[#444] rounded-full px-4 py-2 flex items-center justify-center gap-3 shadow-xl z-20 pointer-events-none"
          >
             <div className="w-3 h-3 rounded-full border-2 border-b-transparent border-white animate-spin"></div>
             <span className="text-white text-sm font-medium tracking-wide">Archimedes is executing...</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Box Area (Fixed at bottom) */}
      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[#0B0B0B] via-[#0B0B0B] to-transparent pt-10 pb-8 flex justify-center px-4">
         <div className="w-full max-w-3xl relative">
           <div className={`bg-[#262626] rounded-[28px] flex flex-col p-2 transition-shadow duration-300 focus-within:shadow-[0_0_0_1px_#555]`}>
             <textarea
               value={input}
               onChange={(e) => setInput(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
               placeholder="Напишите задачу для Archimedes..."
               disabled={isWorking}
               className="w-full bg-transparent border-none text-[#ECECEC] text-[15px] px-4 py-3 outline-none resize-none min-h-[50px] max-h-[200px] placeholder:text-gray-500"
               rows={1}
             />
             
             {/* Bottom row of text area block */}
             <div className="flex items-center justify-between px-2 pb-1 pt-2">
                <div className="flex items-center gap-1">
                   <button onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white hover:bg-[#333] rounded-full transition-colors tooltip tooltip-top" title="Прикрепить файл">
                     <PlusIcon />
                   </button>
                   <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
                   
                   <button 
                     onClick={() => setWebSearchEnabled(!webSearchEnabled)} 
                     className={`p-2 rounded-full transition-colors tooltip tooltip-top ${webSearchEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                     title="Веб-поиск"
                   >
                     <SearchIcon />
                   </button>
                   
                   <button 
                     onClick={() => setGlobeEnabled(!globeEnabled)} 
                     className={`p-2 rounded-full transition-colors tooltip tooltip-top ${globeEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                     title="Сёрфинг и контекст интернета"
                   >
                     <GlobeIcon />
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
                     <MicIcon />
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
           </div>
           
           <div className="text-center mt-3 text-xs text-gray-500 font-medium tracking-wide">
              У Archimedes могут быть ошибки. Пожалуйста, проверяйте важную информацию.
           </div>
         </div>
      </div>

      {/* Artifact Viewer Modal */}
      {viewingArtifact && (
        <ArtifactViewer artifact={viewingArtifact} onClose={() => setViewingArtifact(null)} />
      )}
      
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
