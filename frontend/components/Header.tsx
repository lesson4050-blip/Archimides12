"use client";

import { Plus, History, Settings } from "lucide-react";
import Image from "next/image";

export default function Header({ onNewTask }: { onNewTask?: () => void }) {
  return (
    <header className="h-12 border-b border-[#222] bg-[#0a0a0a] flex items-center justify-between px-4 z-50">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 flex items-center justify-center">
            <Image src="/logo.png" alt="Archimedes Logo" width={32} height={32} className="object-contain" />
        </div>
        <span className="font-bold text-lg tracking-tight">Archimedes</span>
      </div>

      <div className="flex items-center gap-3">
        <button 
          onClick={onNewTask}
          className="flex items-center gap-1.5 px-3 py-1 bg-[#f59e0b] text-black text-sm font-medium rounded-full hover:bg-amber-400 transition-colors shadow-sm hover:shadow-amber-500/20"
        >
          <Plus size={16} />
          <span>New Task</span>
        </button>
        
        <button 
          onClick={() => alert("History feature coming soon!")}
          className="p-2 text-[#9ca3af] hover:text-white hover:bg-[#222] rounded-md transition-colors"
        >
          <History size={18} />
        </button>
        
        <button 
          onClick={() => alert("Settings feature coming soon!")}
          className="p-2 text-[#9ca3af] hover:text-white hover:bg-[#222] rounded-md transition-colors"
        >
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
