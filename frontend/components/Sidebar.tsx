"use client";

import { Edit, Sparkles, Search, Library, Plus, ListFilter, Settings, LayoutGrid, MonitorSmartphone } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import SettingsModal from "./SettingsModal";
import HistoryDrawer from "./HistoryDrawer";
import LibraryDrawer from "./LibraryDrawer";
import AgentModal from "./AgentModal";

interface SidebarProps {
  onNewTask: () => void;
  onAgentSelect?: (agentId: string) => void;
  selectedAgent?: string;
}

export default function Sidebar({ onNewTask, onAgentSelect, selectedAgent }: SidebarProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [isAgentOpen, setIsAgentOpen] = useState(false);

  return (
    <>
    <div className="w-[260px] h-full bg-[#121212] flex flex-col text-white text-sm border-r border-[#222]">
      {/* Header / Logo */}
      <div className="p-5 flex items-center justify-between">
        <div className="flex items-center gap-3 group cursor-pointer">
          <div className="w-8 h-8 flex items-center justify-center overflow-hidden shrink-0 transition-transform group-hover:scale-110">
            <Image src="/logo-optimized.png" alt="Archimedes Logo" width={32} height={32} className="object-contain" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-white to-gray-500 bg-clip-text text-transparent" style={{ fontFamily: "'Inter', sans-serif" }}>
              ARCHIMEDES
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold -mt-0.5">
              1.0 Enterprise
            </span>
          </div>
        </div>
        <button className="text-gray-500 hover:text-white transition-colors">
           <MonitorSmartphone size={20} />
        </button>
      </div>

      {/* Main Actions */}
      <div className="px-3 pt-2 flex flex-col gap-1">
        <button 
          onClick={onNewTask}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[#1f1f1f] transition-colors w-full text-left"
        >
          <Edit size={16} className="text-gray-400" />
          <span>Новое задание</span>
        </button>

        <button 
          onClick={() => setIsAgentOpen(true)}
          className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[#1f1f1f] transition-colors w-full text-left group"
        >
          <div className="flex items-center gap-3">
            <Sparkles size={16} className="text-gray-400 group-hover:text-[#f59e0b] transition-colors" />
            <span>Агенты</span>
          </div>
          <span className="text-[10px] text-blue-400 bg-blue-900/30 px-1.5 py-0.5 rounded font-medium">Новый</span>
        </button>

        <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[#1f1f1f] transition-colors w-full text-left">
          <Search size={16} className="text-gray-400" />
          <span>Поиск</span>
        </button>

        <button 
          onClick={() => setIsLibraryOpen(true)}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[#1f1f1f] transition-colors w-full text-left"
        >
          <Library size={16} className="text-gray-400" />
          <span>Библиотека</span>
        </button>
      </div>

      {/* Projects */}
      <div className="px-3 pt-6 pb-2">
        <div className="flex items-center justify-between text-xs text-gray-500 font-medium px-3 pb-2">
          <span>Проекты</span>
          <button className="hover:text-gray-300 transition-colors"><Plus size={14} /></button>
        </div>
        <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#1f1f1f] transition-colors w-full text-left text-gray-300">
          <Plus size={16} className="text-gray-400" />
          <span>New project</span>
        </button>
      </div>

      {/* History */}
      <div className="px-3 pt-4 flex-1 overflow-y-auto custom-scrollbar">
        <div className="flex items-center justify-between text-xs text-gray-500 font-medium px-3 pb-2">
          <span>Все задачи</span>
          <button onClick={() => setIsHistoryOpen(true)} className="hover:text-gray-300 transition-colors tooltip tooltip-right" title="Полная история"><ListFilter size={14} /></button>
        </div>
        <div className="flex flex-col gap-0.5">
          {/* Active task example */}
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#262626] text-white cursor-pointer group">
            {/* Spinning ring placeholder for active state */}
            <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin shrink-0"></div>
            <span className="truncate text-sm">Текущая задача</span>
          </div>
          
          {/* Inactive tasks */}
          {[
            "Анализ и сравнение Open Source...",
            "Сравнение моего агента с вашим",
            "Пример сложных заданий..."
          ].map((title, i) => (
            <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#1f1f1f] text-gray-300 cursor-pointer group transition-colors">
               <div className="w-4 h-4 text-gray-500">
                 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
               </div>
               <span className="truncate text-sm">{title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 flex items-center justify-between mt-auto">
        <div className="flex items-center gap-3">
          <button onClick={() => setIsSettingsOpen(true)} className="text-gray-400 hover:text-white transition-colors">
            <Settings size={18} />
          </button>
          <button className="text-gray-400 hover:text-white transition-colors">
            <LayoutGrid size={18} />
          </button>
        </div>
        <div className="text-xs text-gray-500 flex items-center gap-1 font-medium">
          from <span className="text-gray-300 font-bold">Google Deepmind</span>
        </div>
      </div>
    </div>
    
    <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    <HistoryDrawer isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />
    <LibraryDrawer isOpen={isLibraryOpen} onClose={() => setIsLibraryOpen(false)} />
    <AgentModal 
      isOpen={isAgentOpen} 
      onClose={() => setIsAgentOpen(false)} 
      onSelect={(id) => {
        if(onAgentSelect) onAgentSelect(id);
        setIsAgentOpen(false);
      }}
      currentSelected={selectedAgent}
    />
    </>
  );
}
