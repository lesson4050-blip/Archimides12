"use client";

import { useState } from "react";
import {
  Sparkles, Monitor, Globe, Search, Code2,
  Table2, BarChart2, Calendar, Users, Mic,
  MessageSquare, ChevronDown, Check
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AGENT_MODES, PRIMARY_MODES, MORE_MODES, AgentMode } from "@/lib/modes";

const ICONS: Record<string, React.ReactNode> = {
  sparkles: <Sparkles size={14} />,
  presentation: <Monitor size={14} />,
  globe: <Globe size={14} />,
  search: <Search size={14} />,
  code: <Code2 size={14} />,
  table: <Table2 size={14} />,
  chart: <BarChart2 size={14} />,
  calendar: <Calendar size={14} />,
  users: <Users size={14} />,
  mic: <Mic size={14} />,
  message: <MessageSquare size={14} />,
};

interface ModeSelectorProps {
  activeMode: string | null;
  onModeChange: (modeId: string | null) => void;
}

export default function ModeSelector({ activeMode, onModeChange }: ModeSelectorProps) {
  const [showMore, setShowMore] = useState(false);
  const [primaryIds, setPrimaryIds] = useState(PRIMARY_MODES);
  const [moreIds, setMoreIds] = useState(MORE_MODES);

  const primaryModes = primaryIds.map(id => AGENT_MODES.find(m => m.id === id)!).filter(Boolean);
  const moreModes = moreIds.map(id => AGENT_MODES.find(m => m.id === id)!).filter(Boolean);

  const handleModeClick = (modeId: string) => {
    if (activeMode === modeId) {
      // Deactivate
      onModeChange(null);
      // Restore original lists
      setPrimaryIds(PRIMARY_MODES);
      setMoreIds(MORE_MODES);
    } else {
      // Activate
      onModeChange(modeId);
      
      // Rotation logic
      if (primaryIds.includes(modeId)) {
        // Move to first position in primary
        const newPrimary = [modeId, ...primaryIds.filter(id => id !== modeId)];
        setPrimaryIds(newPrimary);
      } else if (moreIds.includes(modeId)) {
        // Swap with the first primary mode
        const firstPrimary = primaryIds[0];
        const newPrimary = [modeId, ...primaryIds.slice(1)];
        const newMore = moreIds.map(id => id === modeId ? firstPrimary : id);
        
        setPrimaryIds(newPrimary);
        setMoreIds(newMore);
      }
    }
    setShowMore(false);
  };

  const ModeButton = ({ mode }: { mode: AgentMode }) => {
    const isActive = activeMode === mode.id;
    return (
      <motion.button
        layout
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => handleModeClick(mode.id)}
        className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap border
          ${isActive
            ? "bg-blue-600 text-white border-blue-500 shadow-[0_0_15px_rgba(37,99,235,0.3)]"
            : "bg-[#1A1A1A] text-gray-400 hover:text-gray-200 hover:bg-[#252525] border-[#333]"
          }`}
      >
        <span className={isActive ? "text-white" : "text-gray-500"}>
          {ICONS[mode.icon]}
        </span>
        {mode.label}
      </motion.button>
    );
  };

  return (
    <div className="relative flex items-center gap-2 flex-wrap">
      <AnimatePresence mode="popLayout">
        {primaryModes.map(mode => (
          <ModeButton key={mode.id} mode={mode} />
        ))}
      </AnimatePresence>

      {/* More button */}
      <div className="relative">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowMore(!showMore)}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all border
            ${showMore
              ? "bg-[#2A2A2A] text-white border-[#555] shadow-lg"
              : "bg-[#1A1A1A] text-gray-400 hover:text-gray-200 hover:bg-[#252525] border-[#333]"
            }`}
        >
          <span>More</span>
          <ChevronDown size={12} className={`transition-transform duration-300 ${showMore ? "rotate-180" : ""}`} />
        </motion.button>

        {/* More dropdown */}
        <AnimatePresence>
          {showMore && (
            <>
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowMore(false)} 
              />
              <motion.div 
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute top-full left-0 mt-2 z-50 bg-[#141414] border border-[#2A2A2A] rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] p-1.5 min-w-[220px] max-h-[300px] overflow-y-auto backdrop-blur-xl custom-scrollbar"
              >
                <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-bold">
                  Additional Modes
                </div>
                {moreModes.map(mode => (
                  <button
                    key={mode.id}
                    onClick={() => handleModeClick(mode.id)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all text-left group
                      ${activeMode === mode.id
                        ? "bg-blue-600/10 text-blue-400"
                        : "text-gray-400 hover:bg-[#232323] hover:text-gray-200"
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`transition-colors ${activeMode === mode.id ? "text-blue-400" : "text-gray-500 group-hover:text-gray-400"}`}>
                        {ICONS[mode.icon]}
                      </span>
                      <div>
                        <div className="font-semibold text-xs">{mode.label}</div>
                        {mode.description && (
                          <div className="text-[10px] text-gray-500 mt-0.5 line-clamp-1">{mode.description}</div>
                        )}
                      </div>
                    </div>
                    {activeMode === mode.id && <Check size={14} className="text-blue-400" />}
                  </button>
                ))}
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
