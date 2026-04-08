"use client";

import { useState, useEffect } from "react";
import { X, Settings, Monitor, Moon, Sun, Bell, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [theme, setTheme] = useState("dark");
  const [language, setLanguage] = useState("ru");
  const [notifications, setNotifications] = useState(true);

  // Load from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem("archimedes-theme");
    if (savedTheme) setTheme(savedTheme);
    
    const savedLang = localStorage.getItem("archimedes-language");
    if (savedLang) setLanguage(savedLang);
    
    const savedNotif = localStorage.getItem("archimedes-notifications");
    if (savedNotif) setNotifications(savedNotif === "true");
  }, []);

  // Save to localStorage when changed
  useEffect(() => {
    localStorage.setItem("archimedes-theme", theme);
    localStorage.setItem("archimedes-language", language);
    localStorage.setItem("archimedes-notifications", String(notifications));
  }, [theme, language, notifications]);

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
            className="relative w-full max-w-md bg-[#181818] border border-[#333] rounded-2xl shadow-2xl overflow-hidden flex flex-col text-[#ECECEC]"
          >
            {/* Header */}
            <div className="px-6 py-4 flex items-center justify-between border-b border-[#333]/50">
              <div className="flex items-center gap-3 text-lg font-medium">
                <Settings size={20} className="text-gray-400" />
                Настройки
              </div>
              <button 
                onClick={onClose}
                className="text-gray-400 hover:text-white p-1 rounded-md hover:bg-[#333] transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 flex flex-col gap-6">
              
              {/* Theme */}
              <div className="flex flex-col gap-3">
                <div className="text-sm font-medium text-gray-400 flex items-center gap-2">
                  <Monitor size={16} /> Внешний вид
                </div>
                <div className="flex bg-[#262626] rounded-lg p-1">
                  <button 
                    onClick={() => setTheme("dark")}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm rounded-md transition-all ${theme === "dark" ? "bg-[#333] text-white shadow-sm" : "text-gray-400 hover:text-white"}`}
                  >
                    <Moon size={16} /> Тёмная
                  </button>
                  <button 
                    onClick={() => setTheme("light")}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm rounded-md transition-all ${theme === "light" ? "bg-[#333] text-white shadow-sm" : "text-gray-400 hover:text-white"}`}
                  >
                    <Sun size={16} /> Светлая
                  </button>
                </div>
              </div>

              {/* Language */}
              <div className="flex flex-col gap-3">
                <div className="text-sm font-medium text-gray-400 flex items-center gap-2">
                  <Globe size={16} /> Язык (Language)
                </div>
                <select 
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-[#262626] border border-[#333] text-white text-sm rounded-lg px-4 py-2.5 outline-none focus:border-blue-500 transition-colors cursor-pointer appearance-none"
                >
                  <option value="ru">Русский</option>
                  <option value="en">English</option>
                </select>
              </div>

              {/* Notifications */}
              <div className="flex items-center justify-between mt-2">
                <div className="flex flex-col">
                  <div className="text-sm font-medium text-white flex items-center gap-2">
                    <Bell size={16} className="text-gray-400" /> Уведомления
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">Включить звуковые сигналы</div>
                </div>
                <div 
                  className={`w-11 h-6 rounded-full p-1 cursor-pointer transition-colors ${notifications ? "bg-blue-600" : "bg-[#333]"}`}
                  onClick={() => setNotifications(!notifications)}
                >
                  <motion.div 
                    layout
                    className="w-4 h-4 bg-white rounded-full shadow-sm"
                    animate={{ x: notifications ? 20 : 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                </div>
              </div>

            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-[#121212] border-t border-[#333]/50 flex justify-end">
              <button 
                onClick={onClose}
                className="bg-[#262626] hover:bg-[#333] text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Готово
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
