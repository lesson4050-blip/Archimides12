"use client";

import { Sun, Moon, Monitor as MonitorIcon } from "lucide-react";
import { useSettingsStore } from "@/lib/settingsStore";

export default function GeneralSettingsSection({ updateSettings }: { updateSettings: (v: any) => void }) {
  const { settings } = useSettingsStore();

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-right-2 duration-300">
      <section>
        <h3 className="text-gray-500 text-[13px] font-bold uppercase tracking-wider mb-4">General</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300 mb-2">Language</label>
            <select
              value={settings?.language}
              onChange={(e) => updateSettings({ language: e.target.value })}
              className="w-full max-w-sm bg-white dark:bg-[#141414] border border-gray-200 dark:border-white/10 rounded-xl px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none text-black dark:text-white cursor-pointer"
            >
              <option value="English">English</option>
              <option value="Russian">Russian</option>
              <option value="German">German</option>
            </select>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-gray-500 text-[13px] font-bold uppercase tracking-wider mb-4">Appearance</h3>
        <div className="grid grid-cols-3 gap-4 max-w-xl">
          {[
            { id: "light", icon: Sun, label: "Light" },
            { id: "dark", icon: Moon, label: "Dark" },
            { id: "system", icon: MonitorIcon, label: "System" }
          ].map((theme) => (
            <button
              key={theme.id}
              onClick={() => updateSettings({ theme: theme.id })}
              className={`flex flex-col items-center gap-3 p-6 rounded-2xl border transition-all cursor-pointer relative z-10 ${
                settings?.theme === theme.id
                  ? "border-blue-500 bg-blue-500/5 dark:bg-blue-500/10 shadow-sm"
                  : "border-gray-200 dark:border-white/10 hover:border-gray-300 dark:hover:border-white/20"
              }`}
            >
              <div className={`w-12 h-8 rounded-md flex items-center justify-center ${settings?.theme === theme.id ? "bg-blue-500 text-white" : "bg-gray-100 dark:bg-white/5 text-gray-400"}`}>
                <theme.icon size={18} />
              </div>
              <span className={`text-[13px] font-bold ${settings?.theme === theme.id ? "text-blue-500" : "text-gray-500"}`}>{theme.label}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-gray-500 text-[13px] font-bold uppercase tracking-wider mb-4">Communication</h3>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-[15px] font-bold">Product updates</h4>
              <p className="text-[13px] text-gray-500">Early access to features.</p>
            </div>
            <button
              onClick={() => updateSettings({ product_updates: !settings?.product_updates })}
              className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${settings?.product_updates ? "bg-blue-500" : "bg-gray-300 dark:bg-white/10"}`}
            >
              <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${settings?.product_updates ? "left-7" : "left-1"}`} />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-[15px] font-bold">Email alerts</h4>
              <p className="text-[13px] text-gray-500">Notify when task starts.</p>
            </div>
            <button
              onClick={() => updateSettings({ task_emails: !settings?.task_emails })}
              className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${settings?.task_emails ? "bg-blue-500" : "bg-gray-300 dark:bg-white/10"}`}
            >
              <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${settings?.task_emails ? "left-7" : "left-1"}`} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
