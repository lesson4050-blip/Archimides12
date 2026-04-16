"use client";

import { useState, useEffect } from "react";
import { FileText, Image as ImageIcon, Download, ExternalLink, ChevronUp, ChevronDown, File } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentEvent } from "@/lib/websocket";

export default function ArtifactsDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [artifacts, setArtifacts] = useState<any[]>([]);

  useEffect(() => {
    const handleEvent = (e: any) => {
      const event = e.detail as AgentEvent;
      if (event.type === "message_result" && event.attachments) {
        const newArtifacts = event.attachments.map(path => ( {
          name: path.split("/").pop(),
          path,
          type: path.endsWith(".png") ? "image" : "file"
        }));
        setArtifacts(prev => [...prev, ...newArtifacts]);
      }
      if (event.type === "tool_result" && event.tool === "browser" && event.output && event.output.includes("Screenshot saved")) {
        // Extract screenshot path -- simplified for now
        setArtifacts(prev => [...prev, { name: "Screenshot", type: "image", path: event.output!.split("saved to ")[1] }]);
      }
    };

    window.addEventListener("archimedes-event", handleEvent);
    return () => window.removeEventListener("archimedes-event", handleEvent);
  }, []);

  if (artifacts.length === 0) return null;

  return (
    <div className="absolute bottom-0 right-0 w-[65%] bg-[#111] border-t border-[#222] z-40 transition-all">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full h-8 flex items-center justify-between px-4 text-[10px] font-bold uppercase text-[#9ca3af] hover:text-white hover:bg-[#161616]"
      >
        <div className="flex items-center gap-2">
            <span>Files & Outputs ({artifacts.length})</span>
        </div>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden bg-[#0a0a0a]"
          >
            <div className="p-4 grid grid-cols-2 gap-3 max-h-[300px] overflow-y-auto custom-scrollbar">
              {artifacts.map((art, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-[#111] border border-[#222]">
                  <div className="flex items-center gap-3 overflow-hidden">
                    {art.type === 'image' ? <ImageIcon size={16} className="text-amber-500" /> : <FileText size={16} className="text-blue-500" />}
                    <span className="text-xs truncate font-medium">{art.name}</span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button className="p-1.5 text-[#9ca3af] hover:text-[#f59e0b]"><ExternalLink size={14} /></button>
                    <button className="p-1.5 text-[#9ca3af] hover:text-[#f59e0b]"><Download size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
