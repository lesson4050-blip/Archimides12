"use client";

import { motion, AnimatePresence } from "framer-motion";
import { BrainCircuit, ChevronDown, ChevronRight } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

export default function LiveReasoning({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of thinking block
  useEffect(() => {
    if (isExpanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content, isExpanded]);

  if (!content) return null;

  // Extract thinking content and final response
  let thinkContent = "";
  let finalContent = "";

  const thinkMatch = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/i);
  if (thinkMatch) {
    thinkContent = thinkMatch[1].trim();
    finalContent = content.replace(/<think>[\s\S]*?(?:<\/think>|$)/i, "").trim();
  } else {
    // If no explicit tags, treat everything as final text stream
    finalContent = content;
  }

  // Handle nested JSON tools parsing in the final output (rudimentary cleanup)
  finalContent = finalContent.replace(/```json[\s\S]*?```/gi, "*(Tool Call executing...)*");

  return (
    <div className="flex flex-col gap-2 w-full mt-2">
      {thinkContent && (
        <div className="flex flex-col w-full max-w-[90%] border border-blue-500/20 bg-[#12121A] rounded-xl overflow-hidden shadow-lg">
          <div 
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center justify-between px-4 py-2.5 bg-[#181824] border-b border-blue-500/20 cursor-pointer hover:bg-[#1E1E2E] transition-colors"
          >
            <div className="flex items-center gap-2 text-blue-400 font-medium text-[13px]">
              <BrainCircuit size={16} className={isExpanded ? "animate-pulse text-blue-500" : ""} />
              <span>{isExpanded ? "Live Reasoning Process" : "View reasoning process"}</span>
            </div>
            {isExpanded ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
          </div>
          
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div 
                  ref={scrollRef}
                  className="p-4 text-[13.5px] text-gray-300 font-mono leading-relaxed max-h-[300px] overflow-y-auto custom-scrollbar"
                >
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{thinkContent}</ReactMarkdown>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {finalContent && (
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          className="markdown-content prose prose-invert prose-sm max-w-none text-[#ECECEC] text-[15px] leading-relaxed mt-2"
        >
          <ReactMarkdown>{finalContent}</ReactMarkdown>
        </motion.div>
      )}
    </div>
  );
}
