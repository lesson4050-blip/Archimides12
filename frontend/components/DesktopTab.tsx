"use client";

import { useState } from "react";
import { Monitor, ExternalLink, Keyboard, MousePointer2 } from "lucide-react";
import { AgentEvent } from "@/lib/websocket";

export default function DesktopTab({ events }: { events: AgentEvent[] }) {
  const [isTakeover, setIsTakeover] = useState(false);
  const novncEvent = events.find(e => e.type === "novnc_ready") as any;
  const novncUrl = novncEvent?.url;

  return (
    <div className="h-full flex flex-col bg-black overflow-hidden relative">
      {novncUrl ? (
        <>
          <iframe 
            src={novncUrl} 
            className="flex-1 w-full border-none"
            title="Sandbox Desktop"
          />
          
          <div className="h-10 bg-[#111] border-t border-[#222] flex items-center justify-between px-4 z-10">
            <div className="flex items-center gap-4 text-[10px] text-[#444] font-bold uppercase truncate">
              <span className="flex items-center gap-1"><Monitor size={10} /> 1280×720</span>
              <span className="flex items-center gap-1"><ExternalLink size={10} /> Connected</span>
            </div>
            
            <button 
              onClick={() => setIsTakeover(!isTakeover)}
              className={`px-3 py-1 rounded text-[10px] font-bold uppercase transition-all ${
                isTakeover 
                ? "bg-[#444] text-white" 
                : "bg-[#f59e0b] text-black hover:bg-amber-400 font-extrabold"
              }`}
            >
              {isTakeover ? "Return to Agent" : "Take Control"}
            </button>
          </div>
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-[#222] p-10 text-center">
          <div className="relative mb-6">
            <Monitor size={80} className="opacity-10" />
            <div className="absolute inset-0 flex items-center justify-center">
              <MousePointer2 size={24} className="opacity-20 animate-bounce" />
            </div>
          </div>
          <h3 className="text-lg font-medium text-[#333] mb-1">Desktop view is inactive</h3>
          <p className="max-w-xs text-sm text-[#333]">
            This window will activate automatically when Archimedes opens a browser or requires a visual environment.
          </p>
        </div>
      )}

      {isTakeover && (
        <div className="absolute top-0 left-0 right-0 py-1 bg-amber-500 text-black text-[10px] font-bold uppercase text-center flex items-center justify-center gap-2 px-4 shadow-lg">
          <span className="flex items-center gap-1"><Keyboard size={10} /> Manual Control Active</span>
          <span className="opacity-50">|</span>
          <span>Agent loop is paused until you return.</span>
        </div>
      )}
    </div>
  );
}
