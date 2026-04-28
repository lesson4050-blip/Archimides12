"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Monitor, Bell, Settings, ChevronDown } from "lucide-react";
import { useAppStore } from "@/lib/store";

export default function ChatHeader({ 
  displayTitle,
  hasToolEvents,
  isComputerOpen,
  onToggleComputer
}: { 
  displayTitle: string;
  hasToolEvents: boolean;
  isComputerOpen?: boolean;
  onToggleComputer?: () => void;
}) {
  const { 
    setShowUpdateModal, 
    setIsCheckingUpdate, 
    setShowSettingsModal 
  } = useAppStore();

  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  const handleUpdateClick = () => {
    setShowUpdateModal(true);
    setIsCheckingUpdate(true);
    setTimeout(() => {
      setIsCheckingUpdate(false);
    }, 2000);
  };

  return (
    <div className="h-14 flex items-center justify-between px-6 border-b border-transparent shrink-0 w-full z-10">
       <div className="flex items-center gap-2 font-medium text-[17px] cursor-pointer group hover:bg-[#1A1A1A] px-3 py-1.5 rounded-lg transition-all duration-300">
          <span className="text-gray-200 group-hover:text-white transition-all duration-300 tracking-wide">
            {displayTitle}
          </span>
          <ChevronDown size={14} className="text-gray-500 group-hover:text-gray-300 transition-colors" />
       </div>
        <div className="flex items-center gap-4 relative">
          <button 
            onClick={handleUpdateClick}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 font-medium px-3 py-1.5 rounded-full bg-[#1e293b]/30 hover:bg-[#1e293b]/60 transition-colors"
          >
             <Sparkles size={14} /> Обновление
          </button>
          
          {hasToolEvents && !isComputerOpen && onToggleComputer && (
            <button
              onClick={onToggleComputer}
              className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 font-medium px-3 py-1.5 rounded-full bg-purple-900/20 hover:bg-purple-900/40 transition-colors border border-purple-500/20"
              title="Открыть компьютер агента"
            >
              <Monitor size={14} />
              Компьютер
            </button>
          )}
          
          <div className="h-4 w-px bg-[#333] mx-1"></div>

          <div className="flex items-center gap-3">
             <div className="relative">
               <button 
                 onClick={() => { setShowNotifMenu(!showNotifMenu); setShowProfileMenu(false); }}
                 className={`text-gray-400 hover:text-white transition-colors p-1.5 rounded-md ${showNotifMenu ? 'bg-[#333] text-white' : ''}`}
               >
                 <Bell size={18} />
               </button>
               
               <AnimatePresence>
                 {showNotifMenu && (
                   <motion.div 
                     initial={{ opacity: 0, y: 10 }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0, scale: 0.95 }}
                     className="absolute top-full right-0 mt-2 w-64 bg-[#181818] border border-[#333] rounded-xl shadow-2xl z-50 overflow-hidden"
                   >
                      <div className="px-4 py-3 border-b border-[#333] font-medium text-sm text-white">Уведомления</div>
                      <div className="p-6 flex flex-col items-center justify-center text-gray-500 gap-2">
                         <Bell size={24} className="opacity-40" />
                         <span className="text-xs">Нет новых уведомлений</span>
                      </div>
                   </motion.div>
                 )}
               </AnimatePresence>
             </div>

             <div className="relative">
               <button 
                 onClick={() => { setShowProfileMenu(!showProfileMenu); setShowNotifMenu(false); }}
                 className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-sm font-bold text-white shadow-inner hover:ring-2 hover:ring-teal-400/50 transition-all cursor-pointer"
               >
                 D
               </button>

               <AnimatePresence>
                 {showProfileMenu && (
                   <motion.div 
                     initial={{ opacity: 0, y: 10 }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0, scale: 0.95 }}
                     className="absolute top-full right-0 mt-2 w-56 bg-[#181818] border border-[#333] rounded-xl shadow-2xl z-50 flex flex-col p-1"
                   >
                      <div className="px-3 py-3 border-b border-[#333] flex items-center gap-3 mb-1">
                         <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-sm font-bold text-white">D</div>
                         <div className="flex flex-col">
                           <span className="text-sm font-medium text-white">Developer</span>
                           <span className="text-[10px] text-gray-500">Local Admin</span>
                         </div>
                      </div>
                      <button 
                        onClick={() => { setShowSettingsModal(true); setShowProfileMenu(false); }}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-[#262626] rounded-md transition-colors text-left w-full"
                      >
                         <Settings size={14} /> Настройки
                      </button>
                      <button className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-md transition-colors text-left w-full">
                         Выйти
                      </button>
                   </motion.div>
                 )}
               </AnimatePresence>
             </div>
          </div>
       </div>
    </div>
  );
}
