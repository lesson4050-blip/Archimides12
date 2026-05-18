"use client";

import { motion, AnimatePresence } from "framer-motion";
import MessageItem from "./MessageItem";
import LiveReasoning from "./LiveReasoning";
import { useAppStore } from "@/lib/store";

export default function MessageList({
  messagesEndRef,
}: {
  messagesEndRef: React.RefObject<HTMLDivElement>;
}) {
  const { messages, isWorking, taskElapsed, confidence, suggestions, setInput, setSuggestions, liveReasoning, economyReport, auditTrailId } = useAppStore();

  return (
    <div className="w-full max-w-3xl flex flex-col gap-6">
      <AnimatePresence>
        {messages.map((msg, idx) => {
          const isConsecutive = idx > 0 && messages[idx - 1].role === msg.role && msg.role === "assistant";
          return <MessageItem key={idx} msg={msg} isConsecutive={isConsecutive} />;
        })}
        
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
                 {liveReasoning && <LiveReasoning content={liveReasoning} />}
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
      {/* Economy + Audit Summary */}
      {economyReport && (
        <div className="flex items-center gap-3 mt-2 px-1 text-xs text-gray-500">
          <span>💰 {economyReport.spent_credits}/{economyReport.total_credits} credits</span>
          <span>·</span>
          <span>⚡ {economyReport.efficiency * 100}% efficiency</span>
          {auditTrailId && (
            <>
              <span>·</span>
              <button
                onClick={() => {
                  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
                  window.open(`${apiUrl}/api/audit/${auditTrailId}?format=markdown`, '_blank')
                }}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                🔍 Audit trail
              </button>
            </>
          )}
        </div>
      )}

      <div ref={messagesEndRef as any} />
    </div>
  );
}
