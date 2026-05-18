"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, Wrench, Lightbulb, FileBox } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface MessagePillProps {
  type: "thought" | "tool" | "plan" | "info" | "result";
  title?: string;
  content: string;
  badge?: React.ReactNode;
}

export default function MessagePill({ type, title, content, badge }: MessagePillProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Determine styles and icons based on type
  let icon = <Lightbulb size={14} />;
  let colorClass = "text-yellow-400 bg-yellow-400/10 border-yellow-400/20";
  let defaultTitle = "Thought Process";

  if (type === "tool") {
    icon = <Wrench size={14} />;
    colorClass = "text-blue-400 bg-blue-400/10 border-blue-400/20";
    defaultTitle = "Using Tool";
  } else if (type === "plan") {
    icon = <FileBox size={14} />;
    colorClass = "text-purple-400 bg-purple-400/10 border-purple-400/20";
    defaultTitle = "Plan Strategy";
  }

  const displayTitle = title || defaultTitle;

  return (
    <div className="flex flex-col mb-4 w-full max-w-[90%] font-sans">
      {/* Pill Header */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between px-4 py-2 rounded-full cursor-pointer border transition-colors hover:brightness-110 w-fit ${colorClass}`}
      >
        <div className="flex items-center gap-2 font-medium text-[13px]">
          {icon}
          <span>{displayTitle}</span>
          {badge}
        </div>
        <motion.div
           animate={{ rotate: isOpen ? 90 : 0 }}
           transition={{ duration: 0.2 }}
           className="ml-4 opacity-70"
        >
          <ChevronRight size={14} />
        </motion.div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0, marginTop: 0 }}
            animate={{ height: "auto", opacity: 1, marginTop: 8 }}
            exit={{ height: 0, opacity: 0, marginTop: 0 }}
            className="overflow-hidden"
          >
            <div className="pl-6 border-l-2 border-[#333] ml-4 py-2 text-[14px] text-gray-300">
               <div className="markdown-content prose prose-invert prose-sm max-w-none">
                 <ReactMarkdown>{content}</ReactMarkdown>
               </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
