"use client";

import { useState, useEffect, useRef } from "react";
import { Search, X, Clock, FileText, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery("");
    }
  }, [isOpen]);

  // Handle Cmd+K global shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        // The parent doesn't expose an open function globally, 
        // but typically you'd trigger global state. 
        // For now this just dismisses if open.
      }
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const mockResults = [
    { type: 'history', title: 'Анализ и сравнение Open Source моделей', date: 'Вчера' },
    { type: 'history', title: 'Сравнение моего агента с вашим', date: '2 дня назад' },
    { type: 'file', title: 'Archimedes_Tool_Test_Plan.md', date: 'В проекте' },
    { type: 'file', title: 'globals.css', date: 'В проекте' }
  ];

  const filtered = query 
    ? mockResults.filter(r => r.title.toLowerCase().includes(query.toLowerCase()))
    : mockResults;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="relative w-full max-w-2xl bg-[#181818] border border-[#333] shadow-2xl rounded-xl overflow-hidden text-[#ECECEC]"
          >
            {/* Search Input Bar */}
            <div className="flex items-center px-4 py-4 border-b border-[#333]">
              <Search size={22} className="text-gray-400 mr-3" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск агентов, файлов и задач... (Cmd+K)"
                className="w-full bg-transparent border-none outline-none text-lg placeholder-gray-500"
              />
              <button onClick={onClose} className="p-1 text-gray-500 hover:text-white hover:bg-[#333] rounded-md transition-colors ml-2">
                <X size={18} />
              </button>
            </div>

            {/* Results Area */}
            <div className="max-h-[60vh] overflow-y-auto custom-scrollbar p-2">
              {filtered.length > 0 ? (
                <div className="flex flex-col gap-1">
                  {!query && <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">Недавнее</div>}
                  {filtered.map((item, idx) => (
                    <button 
                      key={idx}
                      onClick={onClose}
                      className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-[#262626] transition-colors group text-left"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        {item.type === 'history' ? (
                          <div className="p-1.5 bg-[#222] rounded-md text-gray-400 group-hover:text-blue-400 transition-colors">
                            <Clock size={16} />
                          </div>
                        ) : (
                          <div className="p-1.5 bg-[#222] rounded-md text-gray-400 group-hover:text-orange-400 transition-colors">
                            <FileText size={16} />
                          </div>
                        )}
                        <span className="truncate">{item.title}</span>
                      </div>
                      <span className="text-xs text-gray-500 shrink-0 ml-4 group-hover:text-gray-400">{item.date}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <Search size={40} className="mb-4 opacity-50 0" />
                  <p>По запросу «{query}» ничего не найдено</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 bg-[#111] border-t border-[#333] flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1"><kbd className="px-1.5 py-0.5 bg-[#222] rounded border border-[#333] text-gray-300 fontFamily-mono">↑</kbd><kbd className="px-1.5 py-0.5 bg-[#222] rounded border border-[#333] text-gray-300 fontFamily-mono">↓</kbd> Навигация</span>
                <span className="flex items-center gap-1"><kbd className="px-1.5 py-0.5 bg-[#222] rounded border border-[#333] text-gray-300 fontFamily-mono">↵</kbd> Выбрать</span>
              </div>
              <span className="flex items-center gap-1"><kbd className="px-1.5 py-0.5 bg-[#222] rounded border border-[#333] text-gray-300 fontFamily-mono">ESC</kbd> Закрыть</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
