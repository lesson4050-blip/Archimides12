"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Search, Plus, Globe, Mic, X } from "lucide-react";
import VoiceVisualizer from "../VoiceVisualizer";
import ModeSelector from "../ModeSelector";
import { useAppStore } from "@/lib/store";

export default function ChatInput({
  currentMode,
  executionMode,
  onModeChange,
  handleSend,
  toggleMic,
  stopTask,
  fileInputRef,
}: {
  currentMode: any;
  executionMode?: "fast" | "planning";
  onModeChange?: (mode: "fast" | "planning") => void;
  handleSend: () => void;
  toggleMic: () => void;
  stopTask: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
}) {
  const {
    input,
    setInput,
    isWorking,
    isListening,
    webSearchEnabled,
    setWebSearchEnabled,
    globeEnabled,
    setGlobeEnabled,
    activeMode,
    setActiveMode,
  } = useAppStore();

  return (
    <motion.div 
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[#0B0B0B] via-[#0B0B0B] to-transparent pt-10 pb-8 flex flex-col items-center px-4 gap-4 z-10 pointer-events-none"
    >
       <div className="w-full max-w-3xl pointer-events-auto">
         <ModeSelector activeMode={activeMode} onModeChange={setActiveMode} />
       </div>
       <div className="w-full max-w-3xl relative pointer-events-auto">
         <motion.div 
           layoutId="input-plaque"
           className={`bg-[#262626] rounded-[28px] flex flex-col p-2 transition-shadow duration-300 focus-within:shadow-[0_0_0_1px_#555]`}
         >
           {isListening ? (
              <div className="w-full h-[60px] flex flex-col items-center justify-center relative">
                 <VoiceVisualizer isActive={isListening} />
                 <div className="absolute right-6 top-1/2 -translate-y-1/2 text-[10px] font-bold text-red-500/80 animate-pulse tracking-widest uppercase">
                   LISTENING...
                 </div>
              </div>
           ) : (
             <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
                placeholder={currentMode.placeholder}
                disabled={isWorking}
                className="w-full bg-transparent border-none text-[#ECECEC] text-[15px] px-4 py-3 outline-none resize-none min-h-[50px] max-h-[200px] placeholder:text-gray-500"
               rows={1}
             />
           )}
           
           <div className="flex items-center justify-between px-2 pb-1 pt-2">
              <div className="flex items-center gap-1">
                 <button onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white hover:bg-[#333] rounded-full transition-colors tooltip tooltip-top" title="Прикрепить файл">
                   <Plus size={14} />
                 </button>
                 
                 <button 
                   onClick={() => setWebSearchEnabled(!webSearchEnabled)} 
                   className={`p-2 rounded-full transition-colors tooltip tooltip-top ${webSearchEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                   title="Веб-поиск"
                 >
                   <Search size={14} />
                 </button>
                 
                 <button 
                   onClick={() => setGlobeEnabled(!globeEnabled)} 
                   className={`p-2 rounded-full transition-colors tooltip tooltip-top ${globeEnabled ? "text-blue-400 bg-blue-900/30" : "text-gray-400 hover:text-white hover:bg-[#333]"}`}
                   title="Сёрфинг и контекст интернета"
                 >
                   <Globe size={14} />
                 </button>

                  <div className="flex items-center ml-2 bg-[#1A1A1A] rounded-full p-0.5 border border-[#333]">
                    <button 
                      onClick={() => onModeChange?.("fast")}
                      className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all ${executionMode === "fast" ? "bg-amber-500/20 text-amber-500 shadow-sm" : "text-gray-500 hover:text-gray-400"}`}
                    >
                      Fast
                    </button>
                    <button 
                      onClick={() => onModeChange?.("planning")}
                      className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all ${executionMode === "planning" ? "bg-blue-500/20 text-blue-500 shadow-sm" : "text-gray-500 hover:text-gray-400"}`}
                    >
                      Plan
                    </button>
                  </div>
              </div>
              
              <div className="flex items-center gap-2">
                 <button 
                   onClick={toggleMic}
                   className={`p-2 rounded-full transition-colors tooltip tooltip-top ${isListening ? "text-red-400 bg-red-900/30 animate-pulse" : "text-gray-400 hover:text-white"}`}
                   title="Голосовой ввод"
                 >
                   <Mic size={16} />
                 </button>
                 {isWorking ? (
                    <button 
                       onClick={stopTask}
                       className="w-8 h-8 rounded-full bg-[#E5E5E5] flex items-center justify-center hover:bg-white transition-colors flex-shrink-0"
                    >
                       <div className="w-3 h-3 bg-black rounded-sm"></div>
                    </button>
                 ) : (
                    <button 
                       onClick={handleSend}
                       disabled={!input.trim()}
                       className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                          input.trim() ? "bg-[#E5E5E5] hover:bg-white text-black" : "bg-[#444] text-[#888]"
                       }`}
                    >
                       <ArrowUpIcon />
                    </button>
                 )}
              </div>
           </div>
         </motion.div>
         
         <div className="text-center mt-3 text-xs text-gray-500 font-medium tracking-wide">
            У Archimedes могут быть ошибки. Пожалуйста, проверяйте важную информацию.
         </div>
       </div>
    </motion.div>
  );
}

function ArrowUpIcon() { 
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="m5 12 7-7 7 7"/>
      <path d="M12 19V5"/>
    </svg>
  );
}
