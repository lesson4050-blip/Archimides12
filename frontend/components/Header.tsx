"use client";

import { Plus, History, Settings } from "lucide-react";

export default function Header() {
  return (
    <header className="h-12 border-b border-[#222] bg-[#0a0a0a] flex items-center justify-between px-4 z-50">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 flex items-center justify-center">
            {/* Logo placeholder - specification says logo will be in /public/logo.png */}
            <div className="w-6 h-6 bg-white rounded-sm"></div>
        </div>
        <span className="font-bold text-lg tracking-tight">Archimedes</span>
      </div>

      <div className="flex items-center gap-3">
        <button 
          className="flex items-center gap-1.5 px-3 py-1 bg-[#f59e0b] text-black text-sm font-medium rounded-full hover:bg-amber-400 transition-colors"
        >
          <Plus size={16} />
          <span>New Task</span>
        </button>
        
        <button className="p-2 text-[#9ca3af] hover:text-white transition-colors">
          <History size={18} />
        </button>
        
        <button className="p-2 text-[#9ca3af] hover:text-white transition-colors">
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
