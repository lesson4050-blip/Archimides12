"use client";

import { useRef, useEffect } from "react";
import { ArchimedesSocket, AgentEvent } from "@/lib/websocket";
import { useAppStore } from "@/lib/store";
import { AGENT_MODES } from "@/lib/modes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export function useArchimedesChat(
  sessionId: string, 
  selectedAgent?: string, 
  executionMode?: "fast" | "planning",
  onStart?: () => void
) {
  const store = useAppStore();
  const socketRef = useRef<ArchimedesSocket | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize speech recognition
  useEffect(() => {
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
          store.setInput((prev) => prev + " " + currentTranscript.trim());
        };
        
        reco.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          store.setIsListening(false);
        };
        
        reco.onend = () => {
          store.setIsListening(false);
        };
        
        recognitionRef.current = reco;
      }
    }
  }, []);

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert("Ваш браузер не поддерживает распознавание речи.");
      return;
    }
    if (store.isListening) {
      recognitionRef.current.stop();
      store.setIsListening(false);
    } else {
      store.setInput("");
      recognitionRef.current.start();
      store.setIsListening(true);
    }
  };

    const bufferRef = useRef<any[]>([]);
    const flushTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // WebSocket Connection with buffering
  useEffect(() => {
    const flushBuffer = () => {
      if (bufferRef.current.length > 0) {
        store.setMessages(prev => [...prev, ...bufferRef.current]);
        bufferRef.current = [];
      }
      if (flushTimeoutRef.current) {
        clearTimeout(flushTimeoutRef.current);
        flushTimeoutRef.current = null;
      }
    };

    const handleAgentEvent = (event: AgentEvent) => {
        if (["message_info", "message_ask", "message_result", "agent_error", "session_end"].includes(event.type)) {
          store.setIsWorking(false);
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
              bufferRef.current.push({ role: "assistant", type: determinedType as any, content: cleaned });
            }
            break;
          }
          case "message_ask": {
            const cleaned = cleanMessageContent(event.text || event.content);
            if (cleaned) bufferRef.current.push({ role: "assistant", type: "ask", content: cleaned });
            break;
          }
          case "message_result": {
            const cleaned = cleanMessageContent(event.text || event.content);
            if (cleaned) bufferRef.current.push({ role: "assistant", type: "result", content: cleaned });
            break;
          }
          case "thought": {
            const cleaned = cleanMessageContent(event.content || event.text);
            if (cleaned) bufferRef.current.push({ role: "assistant", type: "thought", content: cleaned });
            break;
          }
          case "tool_call": {
            bufferRef.current.push({ 
              role: "assistant", 
              type: "tool", 
              content: `Вызов инструмента: **${event.tool}**\n\`\`\`json\n${JSON.stringify(event.params, null, 2)}\n\`\`\`` 
            });
            break;
          }
          case "artifact": {
            const artifactData = {
              name: event.name || "file",
              content: event.content || "",
              path: event.path || event.name || "",
              language: event.language,
            };
            store.setArtifacts(prev => [...prev, artifactData]);
            bufferRef.current.push({ 
              role: "system", 
              type: "artifact", 
              content: event.name || "file",
              artifactData,
            });
            break;
          }
          case "plan_update": {
             bufferRef.current.push({ role: "assistant", type: "plan", content: `Обновление плана: ${event.text || "Выполнение..."}` });
             break;
          }
          case "confidence": {
            store.setConfidence({ score: (event as any).score ?? 100, label: (event as any).label ?? "" });
            break;
          }
          case "suggestions": {
            store.setSuggestions((event as any).items || []);
            break;
          }
          case "file_artifact": {
            const blob = new Blob(
              [Uint8Array.from(atob(event.data || ""), c => c.charCodeAt(0))],
              { type: event.mime_type }
            );
            const url = URL.createObjectURL(blob);
            bufferRef.current.push({
              role: "assistant",
              type: "file_download",
              content: event.label || "Файл сгенерирован",
              filename: event.filename,
              download_url: url,
              size_kb: event.size_kb,
              preview_url: event.preview_url
            });
            break;
          }
          case "browser_navigate": {
            if (typeof window !== "undefined" && window.dispatchEvent) {
               window.dispatchEvent(new CustomEvent("archimedes-open-browser", { detail: { url: event.url, title: event.title } }));
            }
            break;
          }
        }
        
        if (event.type === "tool_call" || event.type === "tool" || event.type === "artifact") {
          store.setHasToolEvents(true);
        }
        window.dispatchEvent(new CustomEvent("archimedes-event", { detail: event }));

        // Batch flushing
        if (!flushTimeoutRef.current) {
          flushTimeoutRef.current = setTimeout(flushBuffer, 100);
        }
    };


    const archSocket = new ArchimedesSocket(sessionId, (event: AgentEvent) => {
      handleAgentEvent(event);
    });
    archSocket.connect();
    socketRef.current = archSocket;

    return () => {
      if (flushTimeoutRef.current) {
        clearTimeout(flushTimeoutRef.current);
      }
      flushBuffer(); // Final flush before unmount
      archSocket.disconnect();
    };
  }, [sessionId]);

  const handleSend = () => {
    if (!store.input.trim() || store.isWorking) return;
    if (!socketRef.current || socketRef.current.getReadyState() !== WebSocket.OPEN) {
      alert("Please wait for connection to establish before sending.");
      return;
    }
    
    const task = store.input.trim();
    store.setMessages(prev => [...prev, { role: "user", type: "text", content: task }]);
    store.setInput("");
    store.setIsWorking(true);
    store.setTaskStartTime(Date.now());
    store.setSuggestions([]);
    store.setConfidence(null);
    if (onStart) onStart();
    
    const currentMode = AGENT_MODES.find(m => m.id === store.activeMode) || AGENT_MODES[0];
    socketRef.current.sendTask(
        task, 
        selectedAgent, 
        executionMode, 
        store.webSearchEnabled, 
        store.globeEnabled, 
        store.activeMode ? currentMode.taskHint : "default"
    );
  };

  const stopTask = () => {
    store.setIsWorking(false);
    store.setTaskStartTime(null);
    store.setMessages(prev => [...prev, { role: "system", type: "info", content: "Task forcibly stopped by user."}]);
  };

  const handleFileUpload = async (e?: React.ChangeEvent<HTMLInputElement>, droppedFile?: File) => {
    const file = droppedFile || e?.target.files?.[0];
    if (!file) return;

    store.setMessages(prev => [...prev, { role: "system", type: "info", content: `Загрузка файла ${file.name}...`}]);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        store.setMessages(prev => [...prev, { role: "system", type: "info", content: `Файл ${file.name} успешно загружен в workspace.`}]);
      } else {
        throw new Error("Upload failed");
      }
    } catch (err) {
       console.error(err);
       store.setMessages(prev => [...prev, { role: "system", type: "info", content: `Ошибка при загрузке ${file.name}.`}]);
    }
  };

  return {
    handleSend,
    stopTask,
    toggleMic,
    handleFileUpload
  };
}
