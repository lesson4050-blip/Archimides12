"use client";

import { Globe, Shield, Cpu, Layout, Mail, Check } from "lucide-react";
import { useSettingsStore } from "@/lib/settingsStore";

const connectorMarketplace = [
  { id: "google-search", name: "Google Search", icon: Globe, desc: "Real-time web search and information retrieval." },
  { id: "brave-search", name: "Brave Search", icon: Shield, desc: "Privacy-focused web search engine." },
  { id: "github-mcp", name: "GitHub Repository", icon: Cpu, desc: "Search and read GitHub repositories." },
  { id: "wolfram", name: "Wolfram Alpha", icon: Layout, desc: "Computational intelligence and data analysis." },
  { id: "slack-mcp", name: "Slack Connect", icon: Mail, desc: "Send and receive messages in Slack channels." },
];

export default function ConnectorsSection({ updateSettings }: { updateSettings: (v: any) => void }) {
  const { settings } = useSettingsStore();

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
      <h3 className="text-xl font-bold mb-6">Marketplace Gallery</h3>
      <div className="grid grid-cols-2 gap-6">
        {connectorMarketplace.map(conn => {
          const isConnected = !!settings?.connectors_json?.[conn.id];
          return (
            <div key={conn.id} className={`p-6 border rounded-2xl flex flex-col gap-4 transition-all ${isConnected ? "border-blue-500 bg-blue-500/[0.02]" : "border-gray-100 dark:border-white/5 bg-white dark:bg-white/[0.02]"}`}>
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${isConnected ? "bg-blue-500 text-white" : "bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400"}`}>
                  <conn.icon size={24} />
                </div>
                <div className="flex-1">
                  <h4 className="text-[15px] font-black mb-1">{conn.name}</h4>
                  <p className="text-[12px] text-gray-500 leading-snug line-clamp-2">{conn.desc}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  const newConn = { ...(settings?.connectors_json || {}), [conn.id]: { command: "npx", args: ["-y", conn.id] } };
                  updateSettings({ connectors_json: newConn });
                }}
                disabled={isConnected}
                className={`w-full py-2.5 rounded-xl text-xs font-black transition-all cursor-pointer ${
                  isConnected
                    ? "bg-emerald-500/10 text-emerald-500 cursor-default"
                    : "bg-black dark:bg-white text-white dark:text-black hover:scale-[1.02] relative z-10"
                }`}
              >
                {isConnected ? (
                  <span className="flex items-center justify-center gap-2"><Check size={14} /> Connected</span>
                ) : "Connect"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
