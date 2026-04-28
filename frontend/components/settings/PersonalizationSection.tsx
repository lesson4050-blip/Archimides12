"use client";

import { useSettingsStore } from "@/lib/settingsStore";
import { Database } from "lucide-react";

export default function PersonalizationSection({ updateSettings, onClose }: { updateSettings: (v: any) => void, onClose: () => void }) {
  const { settings, setSettings, personalizationTab, setPersonalizationTab } = useSettingsStore();

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-right-2 duration-300">
       <p className="text-gray-500 text-[14px]">Manage who you are and what Cosmo remembers</p>
       
       <div className="flex gap-8 border-b border-gray-200 dark:border-white/5 pb-2">
          <button 
            onClick={() => setPersonalizationTab("Profile")}
            className={`text-[14px] font-bold transition-all border-b-2 pb-2 cursor-pointer ${personalizationTab === "Profile" ? "text-black dark:text-white border-black dark:border-white" : "text-gray-400 border-transparent"}`}
          >
            Profile
          </button>
          <button 
            onClick={() => setPersonalizationTab("Knowledge")}
            className={`text-[14px] font-bold transition-all border-b-2 pb-2 cursor-pointer ${personalizationTab === "Knowledge" ? "text-black dark:text-white border-black dark:border-white" : "text-gray-400 border-transparent"}`}
          >
            Knowledge
          </button>
       </div>

       {personalizationTab === "Profile" ? (
        <div className="space-y-8">
          <div className="grid grid-cols-2 gap-6">
             <div className="space-y-2">
                <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300">Nickname</label>
                <input 
                  value={settings?.nickname || ""}
                  onChange={(e) => setSettings({ ...settings, nickname: e.target.value })}
                  placeholder="What should Cosmo call you?"
                  className="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-sm font-medium text-black dark:text-white"
                />
             </div>
             <div className="space-y-2">
                <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300">Occupation</label>
                <input 
                  value={settings?.occupation || ""}
                  onChange={(e) => setSettings({ ...settings, occupation: e.target.value })}
                  placeholder="e.g., Designer, Engineer"
                  className="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-sm font-medium text-black dark:text-white"
                />
             </div>
          </div>

          <div className="space-y-2">
             <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300">More about you</label>
             <textarea 
               value={settings?.bio || ""}
               onChange={(e) => setSettings({ ...settings, bio: e.target.value })}
               placeholder="Your background, preferences, or location"
               className="w-full h-32 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl px-4 py-3 text-sm font-medium resize-none text-black dark:text-white"
             />
          </div>

          <div className="space-y-2">
             <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300">Custom Instructions</label>
             <textarea 
               value={settings?.custom_instructions || ""}
               onChange={(e) => setSettings({ ...settings, custom_instructions: e.target.value })}
               placeholder="How would you like Cosmo to respond?"
               className="w-full h-32 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl px-4 py-3 text-sm font-medium resize-none text-black dark:text-white"
             />
          </div>

          <div className="flex justify-end gap-3 pt-6 border-t border-gray-200 dark:border-white/5">
             <button onClick={onClose} className="px-6 py-2.5 bg-gray-100 dark:bg-white/5 hover:bg-gray-200 dark:hover:bg-white/10 rounded-xl text-sm font-bold transition-colors cursor-pointer">Cancel</button>
             <button 
               onClick={() => {
                 updateSettings({
                   nickname: settings.nickname,
                   occupation: settings.occupation,
                   bio: settings.bio,
                   custom_instructions: settings.custom_instructions
                 });
               }}
               className="px-8 py-2.5 bg-black dark:bg-white text-white dark:text-black hover:scale-105 rounded-xl text-sm font-black shadow-lg transition-transform cursor-pointer relative z-10"
             >
               Save
             </button>
          </div>
        </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 opacity-40">
             <Database size={48} className="mb-4" />
             <h4 className="text-xl font-black mb-2">Knowledge Base</h4>
             <p className="text-sm font-bold text-gray-500">Your custom knowledge and documents will appear here.</p>
          </div>
        )}
    </div>
  );
}
