"use client";

import { useRef, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ArtifactViewer from "./ArtifactViewer";
import SettingsModal from "./SettingsModal";
import { AGENT_MODES } from "@/lib/modes";
import { useAppStore } from "@/lib/store";
import { useArchimedesChat } from "@/hooks/useArchimedesChat";

import ChatHeader from "./chat/ChatHeader";
import EmptyState from "./chat/EmptyState";
import MessageList from "./chat/MessageList";
import ChatInput from "./chat/ChatInput";
import { CheckCircle } from "lucide-react";

export default function ChatPanel({ 
  sessionId, 
  isStarted, 
  onStart, 
  selectedAgent, 
  executionMode,
  onModeChange,
  isComputerOpen, 
  onToggleComputer 
}: { 
  sessionId: string, 
  isStarted: boolean, 
  onStart: () => void, 
  selectedAgent?: string, 
  executionMode?: "fast" | "planning",
  onModeChange?: (mode: "fast" | "planning") => void,
  isComputerOpen?: boolean, 
  onToggleComputer?: () => void 
}) {
  const store = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { handleSend, stopTask, toggleMic, handleFileUpload } = useArchimedesChat(
    sessionId, 
    selectedAgent, 
    executionMode, 
    onStart
  );

  const currentMode = AGENT_MODES.find(m => m.id === store.activeMode) || AGENT_MODES[0];
  const agentDisplayNames: Record<string, string> = {
    "archimedes-cosmo": "Archimedes COSMO",
    "researcher": "Researcher AI",
    "coder": "Coder Bot",
    "data-scientist": "Data Scientist"
  };
  const displayTitle = agentDisplayNames[selectedAgent || "archimedes-cosmo"] || "Archimedes AI";

  // Drag and Drop
  useEffect(() => {
    const handleWindowDragOver = (e: DragEvent) => { e.preventDefault(); setIsDragging(true); };
    const handleWindowDragLeave = (e: DragEvent) => { e.preventDefault(); if (e.relatedTarget === null) setIsDragging(false); };
    const handleWindowDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer?.files[0];
      if (file) handleFileUpload(undefined, file);
    };

    window.addEventListener("dragover", handleWindowDragOver);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);
    return () => {
      window.removeEventListener("dragover", handleWindowDragOver);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
    };
  }, [handleFileUpload]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [store.messages, store.isWorking]);

  // Task Timer
  useEffect(() => {
    if (!store.isWorking || !store.taskStartTime) {
      store.setTaskElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      store.setTaskElapsed(Math.floor((Date.now() - store.taskStartTime!) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [store.isWorking, store.taskStartTime, store.setTaskElapsed]);

  return (
    <div className="flex-1 flex flex-col relative h-full w-full bg-[#0B0B0B] text-[#ECECEC]">
      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
      
      <ChatHeader 
        displayTitle={displayTitle}
        hasToolEvents={store.hasToolEvents}
        isComputerOpen={isComputerOpen}
        onToggleComputer={onToggleComputer}
      />

      <div className={`flex-1 flex flex-col items-center overflow-y-auto custom-scrollbar px-4 transition-all duration-700 ${store.messages.length === 0 ? "justify-center pt-[10vh]" : "pt-10 pb-[22rem]"}`}>
        {store.messages.length === 0 ? (
          <EmptyState 
            currentMode={currentMode}
            handleSend={handleSend}
            toggleMic={toggleMic}
            fileInputRef={fileInputRef}
          />
        ) : (
          <MessageList messagesEndRef={messagesEndRef} />
        )}
      </div>

      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-[100] bg-[#000000a0] backdrop-blur-md flex flex-col items-center justify-center p-12 pointer-events-none"
          >
             <div className="w-full h-full border-2 border-dashed border-blue-500/50 rounded-[40px] flex flex-col items-center justify-center gap-6 bg-gradient-to-br from-blue-500/5 to-purple-500/5">
                <div className="w-24 h-24 rounded-3xl bg-blue-500/20 flex items-center justify-center animate-pulse">
                   <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
                </div>
                <h2 className="text-3xl font-bold text-white tracking-tight">Отпустите файл для загрузки</h2>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {store.messages.length > 0 && (
          <ChatInput 
            currentMode={currentMode}
            executionMode={executionMode}
            onModeChange={onModeChange}
            handleSend={handleSend}
            toggleMic={toggleMic}
            stopTask={stopTask}
            fileInputRef={fileInputRef}
          />
        )}
      </AnimatePresence>

      {store.viewingArtifact && (
        <ArtifactViewer artifact={store.viewingArtifact} onClose={() => store.setViewingArtifact(null)} />
      )}

      {store.showSettingsModal && (
        <SettingsModal isOpen={store.showSettingsModal} onClose={() => store.setShowSettingsModal(false)} />
      )}

      <AnimatePresence>
        {store.showUpdateModal && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => !store.isCheckingUpdate && store.setShowUpdateModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm bg-[#181818] border border-[#333] rounded-2xl p-6 flex flex-col items-center text-center"
            >
              {store.isCheckingUpdate ? (
                <div className="flex flex-col items-center">
                  <div className="w-10 h-10 border-2 border-[#333] border-t-blue-500 animate-spin rounded-full mb-4" />
                  <p className="text-white">Проверка обновлений...</p>
                </div>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center mb-4"><CheckCircle size={24} /></div>
                  <h3 className="text-white font-medium text-lg">Система актуальна</h3>
                  <button onClick={() => store.setShowUpdateModal(false)} className="mt-6 w-full bg-[#262626] py-2 rounded-lg text-white">Понятно</button>
                </>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
