"use client";

import { useState, useEffect, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import ComputerPanel from "@/components/ComputerPanel";
import AgentDashboard from "@/components/AgentDashboard";
import ModelCouncil from "@/components/ModelCouncil";
import DeepResearch from "@/components/DeepResearch";
import { AgentEvent } from "@/lib/websocket";

export default function Home() {
  const [sessionKey, setSessionKey] = useState(0);
  const [sessionId, setSessionId] = useState("");

  useEffect(() => {
    let sid = sessionStorage.getItem("archimedes_session_id");
    if (!sid) {
      sid = `session-${Math.random().toString(36).substring(2, 9)}`;
      sessionStorage.setItem("archimedes_session_id", sid);
    }
    setSessionId(sid);
  }, []);
  const [isStarted, setIsStarted] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState("archimedes-cosmo");
  const [executionMode, setExecutionMode] = useState<"fast" | "planning">("planning");
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);
  const [isCouncilOpen, setIsCouncilOpen] = useState(false);
  const [isResearchOpen, setIsResearchOpen] = useState(false);

  const [isComputerOpen, setIsComputerOpen] = useState(false);

  const userClosedComputerRef = useRef(false);

  useEffect(() => {
    const handleEvent = (e: CustomEvent<AgentEvent>) => {
      const ev = e.detail;
      // Force open and reset manual close on novnc_ready
      if (ev.type === "novnc_ready") {
        userClosedComputerRef.current = false;
        setIsComputerOpen(true);
      } 
      // Auto-open on tool events only if user hasn't manually closed it
      else if ((ev.type === "tool_result" || ev.type === "tool_call" || ev.type === "tool") && !userClosedComputerRef.current) {
        setIsComputerOpen(true);
      }
    };
    window.addEventListener("archimedes-event", handleEvent as EventListener);
    return () => window.removeEventListener("archimedes-event", handleEvent as EventListener);
  }, []);

  const handleNewTask = () => {
    const newSid = `session-${Math.random().toString(36).substring(2, 9)}`;
    sessionStorage.setItem("archimedes_session_id", newSid);
    setSessionId(newSid);
    setSessionKey(prev => prev + 1);
    setIsStarted(false);
    setIsComputerOpen(false);
  };

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-[#0A0A0A] text-white">
      {/* Sidebar Component */}
      <Sidebar 
        onNewTask={handleNewTask} 
        onAgentSelect={setSelectedAgent} 
        selectedAgent={selectedAgent} 
        onDashboardOpen={() => setIsDashboardOpen(true)}
        onToggleComputer={() => {
          const newState = !isComputerOpen;
          setIsComputerOpen(newState);
          if (!newState) userClosedComputerRef.current = true;
          else userClosedComputerRef.current = false;
        }}
        onCouncilOpen={() => setIsCouncilOpen(true)}
        onResearchOpen={() => setIsResearchOpen(true)}
      />
      
      {/* Main Area Layout */}
      {sessionId && (
        <div className="flex-1 flex overflow-hidden h-full">
         
         {/* Left Side: Chat Panel */}
         <div className={`transition-all duration-500 ease-in-out flex flex-col relative h-full ${isComputerOpen ? 'w-1/2 border-r border-[#2A2B3D]' : 'w-full'}`}>
           <ChatPanel 
             key={`chat-${sessionKey}`} 
             sessionId={sessionId} 
             isStarted={isStarted}
             onStart={() => setIsStarted(true)} 
             selectedAgent={selectedAgent}
             executionMode={executionMode}
             onModeChange={setExecutionMode}
             isComputerOpen={isComputerOpen}
             onToggleComputer={() => {
               setIsComputerOpen(true);
               userClosedComputerRef.current = false;
             }}
           />
         </div>

         {/* Right Side: Agent Computer Panel */}
         {isComputerOpen && (
           <div className="w-1/2 h-full relative" style={{ animation: "slideInRight 0.4s ease-out forwards" }}>
             <ComputerPanel key={`comp-${sessionKey}`} sessionId={sessionId} onClose={() => {
               setIsComputerOpen(false);
               userClosedComputerRef.current = true;
             }} />
           </div>
         )}
        </div>
      )}

      {/* Full Screen Agent Dashboard Overlay */}
      {isDashboardOpen && (
        <AgentDashboard onClose={() => setIsDashboardOpen(false)} />
      )}

      {isCouncilOpen && (
        <div className="fixed inset-0 z-50 bg-[#0A0A0A] flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#222]">
            <div className="flex items-center gap-2">
              <span className="text-xl">⚖️</span>
              <span className="font-semibold text-white">Model Council</span>
            </div>
            <button
              onClick={() => setIsCouncilOpen(false)}
              className="text-gray-400 hover:text-white transition-colors text-2xl"
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ModelCouncil />
          </div>
        </div>
      )}

      {isResearchOpen && (
        <div className="fixed inset-0 z-50 bg-[#0A0A0A] flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#222]">
            <div className="flex items-center gap-2">
              <span className="text-xl">🔬</span>
              <span className="font-semibold text-white">Deep Research → Slides</span>
            </div>
            <button
              onClick={() => setIsResearchOpen(false)}
              className="text-gray-400 hover:text-white transition-colors text-2xl"
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <DeepResearch />
          </div>
        </div>
      )}
    </main>
  );
}
