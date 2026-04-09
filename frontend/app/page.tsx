"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import ComputerPanel from "@/components/ComputerPanel";
import { AgentEvent } from "@/lib/websocket";

export default function Home() {
  const [sessionKey, setSessionKey] = useState(0);
  const [sessionId, setSessionId] = useState(() => `session-${Math.random().toString(36).substring(2, 9)}`);
  const [isStarted, setIsStarted] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState("archimedes-cosmo");

  const [isComputerOpen, setIsComputerOpen] = useState(false);

  useEffect(() => {
    const handleEvent = (e: CustomEvent<AgentEvent>) => {
      const ev = e.detail;
      if (ev.type === "tool_call" || ev.type === "tool" || ev.type === "novnc_ready") {
        setIsComputerOpen(true);
      }
    };
    window.addEventListener("archimedes-event", handleEvent as EventListener);
    return () => window.removeEventListener("archimedes-event", handleEvent as EventListener);
  }, []);

  const handleNewTask = () => {
    // Generate a fresh session ID and reset state
    setSessionId(`session-${Math.random().toString(36).substring(2, 9)}`);
    setSessionKey(prev => prev + 1);
    setIsStarted(false);
    setIsComputerOpen(false);
  };

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-[#0A0A0A] text-white">
      {/* Sidebar Component */}
      <Sidebar onNewTask={handleNewTask} onAgentSelect={setSelectedAgent} selectedAgent={selectedAgent} />
      
      {/* Main Area Layout */}
      <div className="flex-1 flex overflow-hidden h-full">
         
         {/* Left Side: Chat Panel */}
         <div className={`transition-all duration-500 ease-in-out flex flex-col relative h-full ${isComputerOpen ? 'w-1/2 border-r border-[#2A2B3D]' : 'w-full'}`}>
           <ChatPanel 
             key={`chat-${sessionKey}`} 
             sessionId={sessionId} 
             isStarted={isStarted}
             onStart={() => setIsStarted(true)} 
             selectedAgent={selectedAgent}
             isComputerOpen={isComputerOpen}
             onToggleComputer={() => setIsComputerOpen(true)}
           />
         </div>

         {/* Right Side: Agent Computer Panel */}
         {isComputerOpen && (
           <div className="w-1/2 h-full relative" style={{ animation: "slideInRight 0.4s ease-out forwards" }}>
             <ComputerPanel key={`comp-${sessionKey}`} sessionId={sessionId} onClose={() => setIsComputerOpen(false)} />
           </div>
         )}
      </div>
    </main>
  );
}
