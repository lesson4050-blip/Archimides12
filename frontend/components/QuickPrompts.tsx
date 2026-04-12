"use client";

import { ArrowUpRight } from "lucide-react";
import { motion } from "framer-motion";

interface QuickPromptsProps {
  prompts: string[];
  onSelect: (prompt: string) => void;
}

export default function QuickPrompts({ prompts, onSelect }: QuickPromptsProps) {
  if (!prompts || prompts.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 w-full">
      {prompts.map((prompt, i) => (
        <motion.button
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          whileHover={{ y: -2, backgroundColor: "#222", borderColor: "#444" }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onSelect(prompt)}
          className="flex items-start justify-between gap-3 p-3.5 rounded-2xl bg-[#1A1A1A] border border-[#2A2A2A]
            transition-all text-left group shadow-lg"
        >
          <span className="text-[13px] text-gray-400 group-hover:text-gray-200 leading-snug transition-colors font-medium">
            {prompt}
          </span>
          <div className="w-6 h-6 rounded-lg bg-[#252525] flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-blue-600/20 group-hover:text-blue-400 transition-all">
            <ArrowUpRight size={14} className="text-gray-600 group-hover:text-blue-400 transition-colors" />
          </div>
        </motion.button>
      ))}
    </div>
  );
}
