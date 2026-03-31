"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentEvent } from "@/lib/websocket";

export default function ThoughtsTab({ events }: { events: AgentEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const thoughtEvents = events.filter(e => e.type === "thought");

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [thoughtEvents]);

  return (
    <div className="h-full bg-[#050505] overflow-y-auto p-6 custom-scrollbar font-mono text-sm leading-relaxed" ref={scrollRef}>
      <div className="max-w-2xl mx-auto space-y-6">
        <AnimatePresence>
          {thoughtEvents.map((event: any, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="relative pl-6 border-l border-[#222]"
            >
              <div className="absolute left-[-1px] top-0 w-[1px] h-4 bg-amber-500/50" />
              <div className="text-[10px] text-[#444] uppercase tracking-widest font-bold mb-2">
                Iteration {event.iteration || idx + 1}
              </div>
              <div className="text-[#9ca3af] whitespace-pre-wrap">
                {event.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {thoughtEvents.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[#333] pt-20">
            <p className="italic">Archemidas is quiet for now...</p>
          </div>
        )}
      </div>
    </div>
  );
}
