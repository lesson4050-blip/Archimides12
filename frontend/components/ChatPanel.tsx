"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Info, User, HelpCircle, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ArchimedesSocket, AgentEvent } from "@/lib/websocket";

import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant" | "system";
  type: "text" | "info" | "ask" | "result";
  content: string;
}

// Utility to strip raw JSON blocks, backticks, <think> blocks, and _TOOL markers for clean display
// Utility to strip raw JSON blocks, backticks, <think> blocks, and _TOOL markers for clean display
const cleanMessageContent = (content: string): string => {
  if (!content) return "";
  
  // 1. Remove <think>...</think> or <thought>...</thought> blocks (common in DeepSeek/Llama)
  let cleaned = content.replace(/<(think|thought)>[\s\S]*?<\/\1>/gi, "");
  
  // 2. Remove any JSON blocks that look like tool calls (looks for { ... "type": ... })
  cleaned = cleaned.replace(/\{[\s\S]*?("type"|"tool_call"|"name"|"params"|"action")[\s\S]*?\}/g, "");
  
  // 3. Remove Manus-style tool call syntax if it leaked into text: message(type="...", content="...")
  cleaned = cleaned.replace(/\w+\(type=["']\w+["'][\s\S]*?\)/g, "");

  // 4. Remove _TOOL: markers and explicit tool names
  cleaned = cleaned.replace(/_TOOL:\s*\w*/g, "");
  
  // 5. Remove any multi-JSON blocks or weird artifacts like "_TOOL: _TOOL:"
  cleaned = cleaned.replace(/_TOOL:\s*/g, "");

  // 6. Remove code block backticks if they wrap JSON or are tiny artifacts
  cleaned = cleaned.replace(/```json[\s\S]*?```/g, "");
  cleaned = cleaned.replace(/```[\s\S]*?```/g, (match) => {
      const lower = match.toLowerCase();
      if (lower.includes("\"tool\"") || lower.includes("\"action\"") || lower.includes("\"name\"") || lower.includes("message(")) return "";
      return match; // Keep legitimate code blocks
  });

  // Final trim and cleanup of multiple newlines
  return cleaned.replace(/\n{3,}/g, "\n\n").trim();
};

export default function ChatPanel({ sessionId, onStart }: { sessionId: string, onStart: () => void }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWorking, setIsWorking] = useState(false);
  const [socket, setSocket] = useState<ArchimedesSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const archSocket = new ArchimedesSocket(sessionId, (event: AgentEvent) => {
      handleAgentEvent(event);
    });
    archSocket.connect();
    setSocket(archSocket);
    return () => archSocket.disconnect();
  }, [sessionId]);

  const handleAgentEvent = (event: AgentEvent) => {
    // Reset isWorking on ANY message from the agent (Bug 3)
    if (["message_info", "message_ask", "message_result", "agent_error", "session_end"].includes(event.type)) {
      setIsWorking(false);
    }

    switch (event.type) {
      case "message_info": {
        const cleaned = cleanMessageContent(event.text);
        if (cleaned) {
          setMessages(prev => [...prev, { role: "assistant", type: "info", content: cleaned }]);
        }
        break;
      }
      case "message_ask": {
        const cleaned = cleanMessageContent(event.text);
        if (cleaned) {
          setMessages(prev => [...prev, { role: "assistant", type: "ask", content: cleaned }]);
        }
        break;
      }
      case "message_result": {
        const cleaned = cleanMessageContent(event.text);
        if (cleaned) {
          setMessages(prev => [...prev, { role: "assistant", type: "result", content: cleaned }]);
        }
        break;
      }
      case "session_end":
      case "agent_error":
        // Already handled by general reset above
        break;
    }
    
    // Dispatch events to other panels
    window.dispatchEvent(new CustomEvent("archimedes-event", { detail: event }));
  };

  const handleSend = () => {
    if (!input.trim() || isWorking) return;
    
    const task = input.trim();
    setMessages(prev => [...prev, { role: "user", type: "text", content: task }]);
    setInput("");
    setIsWorking(true);
    onStart();
    socket?.sendTask(task);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 flex flex-col relative h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-50">
            <div className="w-16 h-16 bg-white rounded-md mb-4 flex items-center justify-center">
              <CheckCircle size={32} className="text-[#f59e0b]" />
            </div>
            <h2 className="text-xl font-medium mb-1">What can I help you with?</h2>
            <p className="text-sm text-[#9ca3af]">"Give me a task. I'll figure out the rest."</p>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div 
                className={`max-w-[85%] p-3 rounded-xl text-sm ${
                  msg.role === "user" 
                  ? "bg-[#f59e0b] text-black font-medium" 
                  : msg.type === "ask" 
                    ? "bg-[#111] border border-amber-500/50" 
                    : msg.type === "result"
                      ? "bg-[#111] border border-green-500/50"
                      : "bg-[#111] text-white"
                }`}
              >
                <div className="flex gap-2">
                  <div className="mt-0.5 shrink-0">
                    {msg.role === "user" ? <User size={14} /> : msg.type === "info" ? <Info size={14} className="text-[#9ca3af]" /> : msg.type === "ask" ? <HelpCircle size={14} className="text-amber-500" /> : <CheckCircle size={14} className="text-green-500" />}
                  </div>
                  <div className="markdown-content prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-[#222]">
        <div className="relative group">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder={isWorking ? "Archimedes is working..." : "Give me a task..."}
            disabled={isWorking}
            className="w-full bg-[#111] border border-[#333] rounded-2xl py-3 pl-4 pr-12 text-sm focus:border-[#f59e0b] focus:ring-1 focus:ring-[#f59e0b] outline-none transition-all resize-none min-h-[60px] max-h-[200px]"
            rows={1}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isWorking}
            className="absolute right-3 bottom-3 p-2 bg-[#f59e0b] text-black rounded-lg disabled:opacity-30 transition-opacity"
          >
            {isWorking ? (
              <div className="flex gap-1">
                <span className="w-1 h-1 bg-black rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1 h-1 bg-black rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1 h-1 bg-black rounded-full animate-bounce"></span>
              </div>
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
