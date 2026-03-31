"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wrench, FileText, Globe, Search, ClipboardList, MessageSquare, ChevronDown, ChevronRight, Check, X, Loader2 } from "lucide-react";
import { AgentEvent } from "@/lib/websocket";

const TOOL_ICONS: Record<string, any> = {
  shell: Wrench,
  file: FileText,
  browser: Globe,
  search: Search,
  plan: ClipboardList,
  message: MessageSquare,
};

export default function ActionsTab({ events }: { events: AgentEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [events]);

  // Group tool_call and tool_result by iteration/idx
  const actionPairs: any[] = [];
  const calls = events.filter(e => e.type === "tool_call");
  const results = events.filter(e => e.type === "tool_result");

  calls.forEach((call: any) => {
    const result = results.find((r: any) => r.tool === call.tool && r.iteration === call.iteration);
    actionPairs.push({ call, result });
  });

  return (
    <div className="h-full overflow-y-auto p-4 custom-scrollbar" ref={scrollRef}>
      <div className="max-w-3xl mx-auto space-y-4 pb-10">
        <AnimatePresence>
          {actionPairs.map((pair, idx) => (
            <ActionCard key={pair.call.iteration || idx} pair={pair} />
          ))}
        </AnimatePresence>
        
        {actionPairs.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[#333] pt-20">
            <p>No actions have been taken yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionCard({ pair }: { pair: any }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = TOOL_ICONS[pair.call.tool] || Wrench;
  const isRunning = !pair.result;
  const isSuccess = pair.result?.success;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-xl overflow-hidden bg-[#111] transition-all ${
        isRunning 
        ? "border-amber-500/30" 
        : isSuccess 
          ? "border-[#222]" 
          : "border-red-500/30"
      }`}
    >
      <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-[#161616]" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center gap-3">
          <div className={`p-1.5 rounded-lg ${isRunning ? "text-amber-500" : isSuccess ? "text-green-500" : "text-red-500"}`}>
            <Icon size={16} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-tight">{pair.call.tool}</span>
              <span className="text-[10px] text-[#444]">iter {pair.call.iteration}</span>
            </div>
            <div className="text-[11px] text-[#9ca3af] font-mono truncate max-w-[300px]">
                {JSON.stringify(pair.call.params).substring(0, 100)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-[10px] font-bold uppercase flex items-center gap-1.5">
            {isRunning ? (
              <><Loader2 size={12} className="animate-spin text-amber-500" /> <span className="text-amber-500">Running</span></>
            ) : isSuccess ? (
              <><Check size={12} className="text-green-500" /> <span className="text-green-500">Done</span></>
            ) : (
              <><X size={12} className="text-red-500" /> <span className="text-red-500">Error</span></>
            )}
          </div>
          <button className="text-[#444] hover:text-[#9ca3af]">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && pair.result && (
        <div className="p-3 pt-0 border-t border-[#222] bg-[#0c0c0c]">
          <div className="mt-3">
            <div className="text-xs font-bold text-[#444] uppercase mb-1">Output</div>
            <pre className="text-[11px] font-mono whitespace-pre-wrap break-all text-[#9ca3af] bg-[#050505] p-3 rounded-lg max-h-[300px] overflow-y-auto custom-scrollbar">
              {pair.result.output || pair.result.error || "No output returned."}
            </pre>
          </div>
        </div>
      )}
    </motion.div>
  );
}
