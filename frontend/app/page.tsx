"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import FloatingDesktop from "@/components/FloatingDesktop";
import ArtifactsDrawer from "@/components/ArtifactsDrawer";

export default function Home() {
  const [sessionKey, setSessionKey] = useState(0);
  const [sessionId, setSessionId] = useState(() => `session-${Math.random().toString(36).substring(2, 9)}`);
  const [isStarted, setIsStarted] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState("archimedes-cosmo");

  const handleNewTask = () => {
    // Generate a fresh session ID and reset state
    setSessionId(`session-${Math.random().toString(36).substring(2, 9)}`);
    setSessionKey(prev => prev + 1);
    setIsStarted(false);
  };

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-[#0A0A0A] text-white">
      {/* Sidebar Component */}
      <Sidebar onNewTask={handleNewTask} onAgentSelect={setSelectedAgent} selectedAgent={selectedAgent} />
      
      {/* Main Chat Area */}
      <div className="flex-1 overflow-hidden h-full flex flex-col relative">
        <ChatPanel 
          key={`chat-${sessionKey}`} 
          sessionId={sessionId} 
          isStarted={isStarted}
          onStart={() => setIsStarted(true)} 
          selectedAgent={selectedAgent}
        />
        {/* Floating Desktop window will be managed conditionally inside ChatPanel or via global state/events */}
        <FloatingDesktop key={`comp-${sessionKey}`} sessionId={sessionId} />
      </div>
    </main>
  );
}
