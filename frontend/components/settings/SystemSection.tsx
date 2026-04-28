"use client";

import { Shield, Monitor, Trash2, Globe } from "lucide-react";
import { useSettingsStore } from "@/lib/settingsStore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function SystemSection({ activeSection, updateSettings, fetchSettings }: { activeSection: string; updateSettings: (v: any) => void; fetchSettings: () => void }) {
  const { settings } = useSettingsStore();

  if (activeSection === "My Computer") {
    return (
      <div className="space-y-10 animate-in fade-in slide-in-from-right-2 duration-300">
        <h3 className="text-2xl font-black mb-8">Access Local Files</h3>
        <div className="bg-amber-500/5 border border-amber-500/10 p-4 rounded-xl text-amber-500 text-xs font-bold flex items-start gap-3">
          <Shield size={16} className="shrink-0" />
          Archimedes will only access the folders you specify below.
        </div>
        <button
          onClick={async () => {
            const path = typeof window !== "undefined" ? prompt("Enter folder path:") : null;
            if (path) {
              const res = await fetch(`${API_BASE}/api/v1/settings/folders`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path })
              });
              if (res.ok) fetchSettings();
              else alert("Failed to add folder.");
            }
          }}
          className="px-8 py-3 bg-black dark:bg-white text-white dark:text-black rounded-2xl text-[13px] font-black shadow-lg cursor-pointer transition-transform hover:scale-105"
        >
          Add Folder
        </button>

        <div className="space-y-4">
          {settings?.connectors_json?.local_folders?.map((path: string, i: number) => (
            <div key={i} className="p-4 border border-gray-100 dark:border-white/5 rounded-xl flex items-center justify-between group translate-all hover:border-blue-500/30">
              <div className="flex items-center gap-3">
                <Monitor size={18} className="text-blue-500" />
                <span className="text-[13px] font-medium text-gray-300">{path}</span>
              </div>
              <button className="text-gray-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 cursor-pointer">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeSection === "Data controls") {
    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
        <div className="flex flex-col gap-6">
          <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
            <div>
              <h4 className="font-black text-lg">Wipe Browser Session</h4>
              <p className="text-sm text-gray-500">Clears cookies, cache and saved logins from the cloud browser.</p>
            </div>
            <button
              onClick={async () => {
                if (typeof window !== "undefined" && confirm("Confirm cleanup? This cannot be undone.")) {
                  await fetch(`${API_BASE}/api/v1/settings/cleanup`, { method: "POST" });
                  alert("Cloud browser is now fresh.");
                }
              }}
              className="px-6 py-2.5 bg-red-500/10 text-red-500 hover:bg-red-500 text-sm font-black rounded-xl transition-all hover:text-white cursor-pointer"
            >
              Fresh Start
            </button>
          </div>

          <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between opacity-40">
            <div>
              <h4 className="font-black text-lg text-gray-300 font-bold">Delete Account</h4>
              <p className="text-sm text-gray-500 font-bold">Permanently remove all data and projects.</p>
            </div>
            <button disabled className="px-6 py-2.5 bg-gray-100 dark:bg-white/5 text-gray-400 text-sm font-black rounded-xl">
              Request Deletion
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (activeSection === "Cloud browser") {
    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
        <div className="flex flex-col gap-6">
          <div className="p-8 bg-blue-500/[0.03] border border-blue-500/10 rounded-3xl flex items-start gap-6">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
              <Globe size={32} />
            </div>
            <div className="flex-1 pt-1">
              <h4 className="font-black text-xl mb-2 text-black dark:text-white">Long-term Session</h4>
              <p className="text-sm text-gray-500 mb-6 font-bold leading-relaxed">By default, Archimedes keeps browser data for up to 30 days. Disable this if you prefer anonymous, fresh browser windows for every task.</p>
              <button
                onClick={() => updateSettings({ browser_persistence: !settings?.browser_persistence })}
                className={`w-14 h-7 rounded-full transition-colors relative cursor-pointer ${settings?.browser_persistence ? "bg-blue-500" : "bg-gray-300 dark:bg-white/10"}`}
              >
                <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all shadow-md ${settings?.browser_persistence ? "left-8" : "left-1"}`} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
              <h4 className="font-black text-black dark:text-white">Current Region</h4>
              <span className="px-3 py-1 bg-gray-100 dark:bg-white/5 rounded-lg text-xs font-black tracking-widest uppercase text-black dark:text-white">Oregon (USA)</span>
            </div>
            <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
              <h4 className="font-black text-black dark:text-white">Concurrency</h4>
              <span className="px-3 py-1 bg-gray-100 dark:bg-white/5 rounded-lg text-xs font-black tracking-widest uppercase text-black dark:text-white">Up to 3 tabs</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
