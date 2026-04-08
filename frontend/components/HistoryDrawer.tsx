"use client";

import { useState, useEffect } from "react";
import { X, Search, Clock, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Task {
  task_id: string;
  description: string;
  status: string;
  created_at: string;
}

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function HistoryDrawer({ isOpen, onClose }: HistoryDrawerProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (isOpen) {
      fetchTasks();
    }
  }, [isOpen]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/tasks");
      const data = await res.json();
      if (data.tasks) {
        setTasks(data.tasks.sort((a: Task, b: Task) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
      }
    } catch (e) {
      console.error("Failed to fetch tasks", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredTasks = tasks.filter(t => t.description?.toLowerCase().includes(search.toLowerCase()));

  const formatDate = (isoString: string) => {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(d);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div 
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-sm bg-[#121212] border-l border-[#333] shadow-2xl flex flex-col text-[#ECECEC]"
          >
            {/* Header */}
            <div className="px-5 py-4 flex items-center justify-between border-b border-[#333]/50 shrink-0">
              <div className="flex items-center gap-3 text-lg font-medium">
                <Clock size={20} className="text-gray-400" />
                История задач
              </div>
              <button 
                onClick={onClose}
                className="text-gray-400 hover:text-white p-1.5 rounded-md hover:bg-[#262626] transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-[#333]/50 shrink-0 bg-[#181818]">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input 
                  type="text"
                  placeholder="Поиск по задачам..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-[#262626] border border-[#333] text-sm text-white rounded-lg pl-9 pr-4 py-2 outline-none focus:border-blue-500 transition-colors placeholder:text-gray-500"
                />
              </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-3 flex flex-col gap-2">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-3">
                  <Loader2 size={24} className="animate-spin text-blue-500" />
                  <span className="text-sm">Загрузка истории...</span>
                </div>
              ) : filteredTasks.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
                  <Clock size={32} className="opacity-50" />
                  <span className="text-sm">Задач не найдено</span>
                </div>
              ) : (
                filteredTasks.map((task, i) => (
                  <div key={i} className="flex flex-col gap-2 p-3 rounded-xl bg-[#1a1a1a] border border-[#2a2a2a] hover:border-[#444] transition-colors cursor-pointer group">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {task.status === "completed" && <CheckCircle size={14} className="text-green-500" />}
                        {task.status === "failed" && <AlertCircle size={14} className="text-red-500" />}
                        {task.status === "pending" && <div className="w-3.5 h-3.5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />}
                        <span className="text-xs font-medium text-gray-400 capitalize">{task.status}</span>
                      </div>
                      <span className="text-[11px] text-gray-500">{formatDate(task.created_at)}</span>
                    </div>
                    <p className="text-sm text-gray-200 line-clamp-2 leading-relaxed">
                      {task.description || "Без описания"}
                    </p>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
