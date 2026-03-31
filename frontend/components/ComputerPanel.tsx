"use client";

import { useState, useEffect } from "react";
import { ClipboardList, Brain, Zap, Monitor } from "lucide-react";
import PlanTab from "./PlanTab";
import ThoughtsTab from "./ThoughtsTab";
import ActionsTab from "./ActionsTab";
import DesktopTab from "./DesktopTab";
import { AgentEvent } from "@/lib/websocket";

export default function ComputerPanel({ sessionId }: { sessionId: string }) {
  const [activeTab, setActiveTab] = useState<"plan" | "thoughts" | "actions" | "desktop">("plan");
  const [events, setEvents] = useState<AgentEvent[]>([]);

  useEffect(() => {
    const handleEvent = (e: any) => {
      const event = e.detail as AgentEvent;
      setEvents(prev => [...prev, event]);
      
      // Auto-switch tabs based on event type if desired
      if (event.type === "plan_update") setActiveTab("plan");
      if (event.type === "thought") setActiveTab("thoughts");
      if (event.type === "tool_call") setActiveTab("actions");
    };

    window.addEventListener("archimedes-event", handleEvent);
    return () => window.removeEventListener("archimedes-event", handleEvent);
  }, []);

  const tabs = [
    { id: "plan", label: "Plan", icon: ClipboardList },
    { id: "thoughts", label: "Thoughts", icon: Brain },
    { id: "actions", label: "Actions", icon: Zap },
    { id: "desktop", label: "Desktop", icon: Monitor },
  ] as const;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tab Bar */}
      <div className="flex bg-[#0a0a0a] border-b border-[#222]">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold transition-all border-b-2 ${
              activeTab === tab.id 
              ? "border-[#f59e0b] text-[#f59e0b] bg-[#111]" 
              : "border-transparent text-[#9ca3af] hover:text-white hover:bg-[#111]"
            }`}
          >
            <tab.icon size={14} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden relative">
        <div className={`h-full ${activeTab === "plan" ? "block" : "hidden"}`}>
          <PlanTab events={events.filter(e => e.type === "plan_update")} />
        </div>
        <div className={`h-full ${activeTab === "thoughts" ? "block" : "hidden"}`}>
          <ThoughtsTab events={events.filter(e => e.type === "thought")} />
        </div>
        <div className={`h-full ${activeTab === "actions" ? "block" : "hidden"}`}>
          <ActionsTab events={events.filter(e => e.type === "tool_call" || e.type === "tool_result")} />
        </div>
        <div className={`h-full ${activeTab === "desktop" ? "block" : "hidden"}`}>
          <DesktopTab events={events.filter(e => e.type.startsWith("novnc"))} />
        </div>
      </div>
    </div>
  );
}
