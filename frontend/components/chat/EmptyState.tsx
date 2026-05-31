"use client";

import { motion } from "framer-motion";
import VoiceVisualizer from "../VoiceVisualizer";
import ModeSelector from "../ModeSelector";
import ModeDiscovery from "../ModeDiscovery";
import { Search, Plus, Globe, Mic, X, Scale, Microscope, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";

export default function EmptyState({
  currentMode,
  handleSend,
  toggleMic,
  fileInputRef,
  onCouncilOpen,
  onResearchOpen,
}: {
  currentMode: any;
  handleSend: () => void;
  toggleMic: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onCouncilOpen?: () => void;
  onResearchOpen?: () => void;
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

  const [isPillHovered, setIsPillHovered] = require("react").useState(false);

  return (
    <div className="w-full max-w-3xl flex flex-col items-center">
      <motion.h1 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-[40px] md:text-[56px] font-serif mb-12 text-center text-white/95 font-medium leading-tight tracking-tight px-4"
      >
         What can I do for you?
      </motion.h1>
      
      {/* The "Plaque" (Input Area) centered */}
      <div className="w-full flex flex-col items-center gap-6">
          <motion.div 
            layoutId="input-plaque"
            className="w-full bg-[#181818] border border-[#2A2A2A] rounded-[32px] p-2 px-1 shadow-2xl relative"
          >
            {isListening ? (
               <div className="w-full flex items-center justify-center py-5 min-h-[60px]">
                  <VoiceVisualizer isActive={isListening} />
               </div>
            ) : (
              <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
                  placeholder={currentMode.placeholder}
                  disabled={isWorking}
                  className="w-full bg-transparent border-none text-[#ECECEC] text-[17px] px-6 py-5 outline-none resize-none min-h-[60px] max-h-[200px] placeholder:text-gray-500 font-medium"
                  rows={1}
              />
            )}
            <div className="flex items-center justify-between px-4 pb-3 pt-1">
                <div className="flex items-center gap-3">
                    <button onClick={() => fileInputRef.current?.click()} className="p-2.5 text-gray-500 hover:text-white hover:bg-[#222] rounded-xl transition-all">
                        <Plus size={18} />
                    </button>
                    <div className="h-5 w-px bg-white/5 mx-1"></div>
                    <button 
                      onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                      className={`p-2.5 rounded-xl transition-all ${webSearchEnabled ? "text-blue-400 bg-blue-900/20" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                    >
                        <Search size={18} />
                    </button>
                    <button 
                      onClick={() => setGlobeEnabled(!globeEnabled)}
                      className={`p-2.5 rounded-xl transition-all ${globeEnabled ? "text-blue-400 bg-blue-900/20" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                    >
                        <Globe size={18} />
                    </button>
                    
                    {/* Active Mode Pill inside input */}
                    {activeMode && activeMode !== "default" && (
                       <motion.button 
                         initial={{ scale: 0.9, opacity: 0 }}
                         animate={{ scale: 1, opacity: 1 }}
                         onMouseEnter={() => setIsPillHovered(true)}
                         onMouseLeave={() => setIsPillHovered(false)}
                         onClick={() => setActiveMode(null)}
                         className="flex items-center gap-2 bg-blue-600/10 hover:bg-red-500/10 text-blue-400 hover:text-red-400 px-3.5 py-1.5 rounded-full border border-blue-500/20 hover:border-red-500/30 text-xs font-bold transition-all group/pill"
                       >
                          {isPillHovered ? (
                            <>
                              <X size={12} className="shrink-0" />
                              <span>Cancel {currentMode.label}</span>
                            </>
                          ) : (
                            <>
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
                              {currentMode.label}
                            </>
                          )}
                       </motion.button>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <button 
                      onClick={toggleMic}
                      className={`p-2.5 rounded-xl transition-all ${isListening ? "text-red-400 bg-red-900/10 animate-pulse" : "text-gray-500 hover:text-white hover:bg-[#222]"}`}
                    >
                        <Mic size={18} />
                    </button>
                    <button 
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${input.trim() ? "bg-white text-black hover:scale-105" : "bg-[#222] text-gray-600"}`}
                    >
                        <ArrowUpIcon />
                    </button>
                </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="w-full flex justify-center py-2"
          >
             <ModeSelector activeMode={activeMode} onModeChange={setActiveMode} />
          </motion.div>

          {/* Quick Tool Buttons */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex items-center gap-2 flex-wrap justify-center mt-6 mb-4"
          >
            {[
              { icon: <Scale size={15} className="text-gray-400 group-hover:text-white transition-colors" />, label: 'Model Council', desc: 'Compare models', onClick: onCouncilOpen },
              { icon: <Microscope size={15} className="text-gray-400 group-hover:text-white transition-colors" />, label: 'Deep Research', desc: 'Research → Slides', onClick: onResearchOpen },
              { icon: <Sparkles size={15} className="text-gray-400 group-hover:text-white transition-colors" />, label: 'Ask anything', desc: 'General chat', onClick: () => {} },
              { icon: <Globe size={15} className="text-gray-400 group-hover:text-white transition-colors" />, label: 'Build website', desc: 'Create web app', onClick: () => setInput('Build a website for ') },
              { icon: <Search size={15} className="text-gray-400 group-hover:text-white transition-colors" />, label: 'Wide Research', desc: 'Deep analysis', onClick: () => setInput('Research and analyze: ') },
            ].map((tool) => (
              <button
                key={tool.label}
                onClick={tool.onClick}
                className="flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 
                           border border-white/10 hover:border-white/20 rounded-xl 
                           text-sm text-gray-300 hover:text-white transition-all group"
              >
                {tool.icon}
                <span>{tool.label}</span>
              </button>
            ))}
          </motion.div>
      </div>

      <ModeDiscovery 
        mode={currentMode} 
        onSelectPrompt={(p) => setInput(p)}
        onSelectTemplate={(t) => {
            setInput(
                `Создай профессиональную презентацию на тему: [тема]. ` +
                `Включи: введение, ключевые проблемы, решение, данные и факты, ` +
                `выводы. Используй шаблон ${t}. Слайдов: 8.`
            );
        }}
      />
    </div>
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
