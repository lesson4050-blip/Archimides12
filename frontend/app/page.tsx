"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import ChatPanel from "@/components/ChatPanel";
import ComputerPanel from "@/components/ComputerPanel";
import ArtifactsDrawer from "@/components/ArtifactsDrawer";

export default function Home() {
  const [sessionId] = useState(() => `session-${Math.random().toString(36).substring(2, 9)}`);
  const [isStarted, setIsStarted] = useState(false);

  return (
    <main className="flex flex-col h-screen w-screen overflow-hidden bg-[#0a0a0a] text-white">
      <Header />
      
      <div className="flex flex-1 overflow-hidden h-full">
        {/* Left Panel: Chat Interface (35%) */}
        <div className="w-[35%] h-full border-r border-[#222] flex flex-col overflow-hidden">
          <ChatPanel sessionId={sessionId} onStart={() => setIsStarted(true)} />
        </div>

        {/* Right Panel: Archimedes's Computer (65%) */}
        <div className="w-[65%] h-full bg-[#050505] flex flex-col relative overflow-hidden">
          {isStarted ? (
            <>
              <ComputerPanel sessionId={sessionId} />
              <ArtifactsDrawer />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-[#444] italic">
              Archimedes's workspace will activate once you provide a task.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
