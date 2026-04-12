"use client";

import { X, Folder, Plus, FileText, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface ProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ProjectModal({ isOpen, onClose }: ProjectModalProps) {
  const [projectName, setProjectName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = () => {
    if (!projectName.trim()) return;
    setIsCreating(true);
    // Simulate creation delay
    setTimeout(() => {
      setIsCreating(false);
      setProjectName("");
      onClose();
    }, 1500);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="relative w-full max-w-md bg-[#121212] border border-[#2A2B3D] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-[#2A2B3D]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-blue-500/20 border border-indigo-500/20 flex items-center justify-center">
                  <Folder className="text-indigo-400" size={20} />
                </div>
                <div className="flex flex-col">
                  <h2 className="text-lg font-bold text-white tracking-wide">Новый проект</h2>
                  <span className="text-xs text-gray-500">Изолированное окружение для агента</span>
                </div>
              </div>
              <button 
                onClick={onClose}
                className="text-gray-500 hover:text-white transition-colors p-2 rounded-lg hover:bg-[#1A1A1A]"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-300">Название проекта</label>
                <div className="relative">
                  <input 
                    type="text" 
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Например, My NextJS Startup" 
                    className="w-full bg-[#1A1A1A] border border-[#333] rounded-xl px-4 py-3 text-white text-sm outline-none focus:border-indigo-500/50 transition-colors placeholder:text-gray-600"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-300">Шаблон (опционально)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col items-center justify-center gap-2 border border-indigo-500/50 bg-indigo-500/10 rounded-xl p-4 cursor-pointer transition-colors">
                    <Globe size={24} className="text-indigo-400" />
                    <span className="text-xs font-medium text-indigo-300">Web App</span>
                  </div>
                  <div className="flex flex-col items-center justify-center gap-2 border border-[#333] hover:border-[#444] bg-[#1A1A1A] rounded-xl p-4 cursor-pointer transition-colors group">
                    <FileText size={24} className="text-gray-500 group-hover:text-gray-400" />
                    <span className="text-xs font-medium text-gray-500 group-hover:text-gray-400">Empty</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-5 border-t border-[#2A2B3D] bg-[#0A0A0A] flex justify-end gap-3">
              <button 
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl font-medium text-sm text-gray-400 hover:text-white hover:bg-[#222] transition-colors"
              >
                Отмена
              </button>
              <button 
                onClick={handleCreate}
                disabled={!projectName.trim() || isCreating}
                className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm transition-all shadow-lg ${
                  projectName.trim() && !isCreating
                    ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-900/50" 
                    : "bg-[#222] text-gray-500 cursor-not-allowed"
                }`}
              >
                {isCreating ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/20 border-t-white animate-spin"></div>
                    Создание...
                  </>
                ) : (
                  <>
                    <Plus size={16} /> Создать проект
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
