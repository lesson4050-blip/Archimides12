"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentEvent } from "@/lib/websocket";

export default function PlanTab({ events }: { events: AgentEvent[] }) {
  const lastEvent = events[events.length - 1];
  const phases = lastEvent?.type === "plan_update" ? lastEvent.phases : [];

  return (
    <div className="p-6 h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-xl mx-auto space-y-4">
        <AnimatePresence>
          {phases.map((phase: any, idx: number) => (
            <motion.div
              key={phase.id || idx}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`p-4 rounded-xl border transition-all ${
                phase.status === "active"
                  ? "bg-[#111] border-amber-500/50 shadow-lg shadow-amber-500/5"
                  : phase.status === "complete"
                    ? "bg-[#111] border-[#222] opacity-80"
                    : "bg-transparent border-[#222] opacity-50"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="shrink-0">
                  {phase.status === "complete" ? (
                    <CheckCircle2 className="text-green-500" size={20} />
                  ) : phase.status === "active" ? (
                    <Loader2 className="text-amber-500 animate-spin" size={20} />
                  ) : (
                    <Circle className="text-[#333]" size={20} />
                  )}
                </div>
                <div>
                  <div className="text-xs text-[#9ca3af] uppercase tracking-wider font-semibold mb-0.5">
                    Phase {idx + 1}
                  </div>
                  <div className={`text-sm font-medium ${phase.status === 'active' ? 'text-white' : 'text-[#9ca3af]'}`}>
                    {phase.title}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {phases.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[#444] pt-20">
            <ClipboardList size={40} className="mb-2 opacity-20" />
            <p>Waiting for Archimedes to create a plan...</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { ClipboardList } from "lucide-react";
