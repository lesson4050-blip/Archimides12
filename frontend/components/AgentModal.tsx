"use client";

import { useState, useEffect } from "react";
import { X, Bot, Sparkles, BrainCircuit, Search as SearchIcon, Code, Beaker } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface AgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect?: (agentId: string) => void;
  currentSelected?: string;
}

const AGENTS = [
  {
    id: "archimedes-cosmo",
    name: "Archimedes COSMO",
    version: "2.0",
    role: "Осн. Агент",
    description: "Универсальный помощник. Программирование, анализ, управление ПК.",
    icon: <Sparkles size={24} className="text-amber-500" />
  },
  {
    id: "researcher",
    name: "Researcher AI",
    version: "1.2",
    role: "Аналитик",
    description: "Глубокий поиск информации, анализ данных, составление отчетов.",
    icon: <SearchIcon size={24} className="text-blue-500" />
  },
  {
    id: "coder",
    name: "Coder Bot",
    version: "1.5",
    role: "Разработчик",
    description: "Написание кода, рефакторинг, ревью, тесты.",
    icon: <Code size={24} className="text-green-500" />
  },
  {
    id: "data-scientist",
    name: "Data Scientist",
    version: "1.0",
    role: "Экспериментатор",
    description: "Анализ датасетов, ML модели, статистика, визуализация.",
    icon: <Beaker size={24} className="text-purple-500" />
  }
];

export default function AgentModal({ isOpen, onClose, onSelect, currentSelected }: AgentModalProps) {
  const [selected, setSelected] = useState(currentSelected || AGENTS[0].id);

  // Sync internal state if prop changes
  useEffect(() => {
    if (currentSelected) setSelected(currentSelected);
  }, [currentSelected]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="relative w-full max-w-2xl bg-[#181818] border border-[#333] rounded-2xl shadow-2xl overflow-hidden flex flex-col text-[#ECECEC]"
          >
            {/* Header */}
            <div className="px-6 py-4 flex items-center justify-between border-b border-[#333]/50">
              <div className="flex items-center gap-3 text-lg font-medium">
                <Bot size={20} className="text-gray-400" />
                Выбор Агента
              </div>
              <button 
                onClick={onClose}
                className="text-gray-400 hover:text-white p-1 rounded-md hover:bg-[#333] transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#121212]">
               {AGENTS.map(agent => (
                 <div 
                   key={agent.id}
                   onClick={() => setSelected(agent.id)}
                   className={`p-4 rounded-xl border flex flex-col gap-3 cursor-pointer transition-all ${selected === agent.id ? "bg-[#2a2a2a] border-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.5)]" : "bg-[#1f1f1f] border-[#333] hover:border-[#555]"}`}
                 >
                    <div className="flex items-center justify-between">
                       <div className="w-10 h-10 rounded-lg bg-[#111] border border-[#222] flex items-center justify-center shadow-inner">
                          {agent.icon}
                       </div>
                       <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500 bg-[#111] px-2 py-1 rounded">
                          {agent.role}
                       </span>
                    </div>
                    <div>
                       <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{agent.name}</span>
                          <span className="text-xs text-gray-500">v{agent.version}</span>
                       </div>
                       <p className="text-xs text-gray-400 mt-1 leading-relaxed line-clamp-2">
                          {agent.description}
                       </p>
                    </div>
                 </div>
               ))}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-[#181818] border-t border-[#333]/50 flex justify-between items-center">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                 <BrainCircuit size={14} /> Подключено к LLM backend
              </div>
              <button 
                onClick={() => {
                  if (onSelect) onSelect(selected);
                  else onClose();
                }}
                className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-900/20"
              >
                Выбрать агента
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
