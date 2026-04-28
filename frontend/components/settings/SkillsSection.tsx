"use client";

import { Search, RotateCcw, Plus } from "lucide-react";
import { useSettingsStore } from "@/lib/settingsStore";

export default function SkillsSection({ updateSettings, fetchSettings }: { updateSettings: (v: any) => void; fetchSettings: () => void }) {
  const { settings } = useSettingsStore();

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              placeholder="Search Skill"
              className="w-full bg-gray-50 dark:bg-[#141414] border border-gray-100 dark:border-white/5 rounded-xl pl-10 pr-4 py-2 text-sm text-black dark:text-white"
            />
          </div>
          <button onClick={fetchSettings} className="p-2 bg-gray-100 dark:bg-white/5 rounded-lg text-gray-400 cursor-pointer">
            <RotateCcw size={16} />
          </button>
        </div>
        <button
          onClick={() => {
            const name = typeof window !== "undefined" ? prompt("Enter Skill ID:") : null;
            if (name) {
              const newSkills = { ...(settings?.skills_json || {}), [name]: true };
              updateSettings({ skills_json: newSkills });
            }
          }}
          className="flex items-center gap-2 px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-xl text-sm font-black shadow-lg cursor-pointer transition-transform hover:scale-105"
        >
          <Plus size={16} /> Add
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[
          { id: "bgm-prompter", title: "bgm-prompter", desc: "MUST read this skill BEFORE music tasks." },
          { id: "video-gen", title: "video-generator", desc: "Professional AI video production workflow." },
          { id: "stock-analysis", title: "stock-analysis", desc: "Analyze markets using financial data." }
        ].map(skill => {
          const isActive = settings?.skills_json?.[skill.id] ?? false;
          return (
            <div key={skill.id} className={`p-5 border rounded-2xl space-y-3 transition-all ${isActive ? "border-blue-500 bg-blue-500/[0.03]" : "border-gray-100 dark:border-white/5 bg-gray-50/30 dark:bg-white/[0.02]"}`}>
              <div className="flex items-center justify-between">
                <h4 className="font-black truncate mr-2">{skill.title}</h4>
                <button
                  onClick={() => {
                    const newSkills = { ...(settings?.skills_json || {}), [skill.id]: !isActive };
                    updateSettings({ skills_json: newSkills });
                  }}
                  className={`w-10 h-5 rounded-full relative transition-colors cursor-pointer shrink-0 ${isActive ? "bg-blue-500" : "bg-gray-300 dark:bg-white/10"}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${isActive ? "left-5" : "left-1"}`} />
                </button>
              </div>
              <p className="text-[11px] text-gray-500 font-medium leading-relaxed line-clamp-2">{skill.desc}</p>
              <div className="flex items-center gap-2 pt-2 text-[10px] text-gray-400 font-bold uppercase tracking-widest">
                <div className="w-1 h-1 rounded-full bg-gray-400" /> Official
                <div className="w-1 h-1 rounded-full bg-gray-400 ml-2" /> Updated: Apr 1, 2026
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
