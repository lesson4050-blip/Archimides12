"use client";

import { useState, useEffect } from "react";
import { Monitor, X, Expand } from "lucide-react";
import { AgentEvent } from "@/lib/websocket";
import { motion, AnimatePresence } from "framer-motion";

export default function FloatingDesktop({ sessionId }: { sessionId: string }) {
  const [novncUrl, setNovncUrl] = useState<string | null>(null);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // We listen to the global archimedes events dispatched by ChatPanel
    const handleEvent = (e: any) => {
      const event = e.detail as AgentEvent;
      if (event.type === "novnc_ready" && (event as any).url) {
        setNovncUrl((event as any).url);
        setIsMinimized(false);
      }
      if (event.type === "session_end" || event.type === "agent_error") {
        // Option to optionally clear it, but let's keep it visible until manually closed
      }
    };

    window.addEventListener("archimedes-event", handleEvent);
    return () => window.removeEventListener("archimedes-event", handleEvent);
  }, []);

  if (!novncUrl) return null;

  return (
    <AnimatePresence>
      {!isMinimized && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className={`absolute ${
            isExpanded 
              ? "inset-4 z-50 rounded-2xl shadow-2xl" 
              : "bottom-6 left-6 w-[400px] h-[300px] rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.5)] z-40"
          } bg-[#1e1e1e] border border-[#333] flex flex-col overflow-hidden transition-all duration-300`}
        >
          {/* Header */}
          <div className="h-8 bg-[#262626] border-b border-[#333] flex items-center justify-between px-3 shrink-0">
            <div className="flex items-center gap-2 text-xs text-gray-300 font-medium tracking-wide">
              <Monitor size={12} className="text-[#f59e0b]" />
              <span>Archimedes Desktop</span>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-gray-400 hover:text-white transition-colors"
                title={isExpanded ? "Restore" : "Maximize"}
              >
                <Expand size={14} />
              </button>
              <button 
                onClick={() => setIsMinimized(true)}
                className="text-gray-400 hover:text-white transition-colors"
                title="Close Viewer"
              >
                <X size={14} />
              </button>
            </div>
          </div>
          
          {/* Iframe content */}
          <div className="flex-1 w-full bg-black relative">
            <iframe 
              src={novncUrl} 
              className="absolute inset-0 w-full h-full border-none pointer-events-auto"
              title="Sandbox Desktop Stream"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
