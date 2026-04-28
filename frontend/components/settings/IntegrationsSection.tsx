"use client";

import { useSettingsStore } from "@/lib/settingsStore";
import { Cable, Plug, Mail, Shield, Check, Save } from "lucide-react";

export default function IntegrationsSection({ updateSettings }: { updateSettings: (v: any) => void }) {
  const { settings, setSettings } = useSettingsStore();

  const integrations = [
    { id: "api", title: "Cosmo API", desc: "Build custom integrations.", icon: Cable, key: "api_key" },
    { id: "zapier", title: "Zapier", desc: "Connect thousands of apps.", icon: Plug, key: "zapier_key" },
    { id: "slack", title: "Slack", desc: "Assign tasks via @Cosmo in Slack.", icon: Mail, key: "slack_webhook" },
    { id: "github", title: "GitHub Bot", desc: "Automate your repositories.", icon: Shield, key: "github_token" }
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
       <p className="text-sm font-medium text-gray-500 font-bold">Build workflows across your favorite apps</p>
       <div className="grid grid-cols-2 gap-6">
          {integrations.map(integration => (
            <div key={integration.id} className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex flex-col gap-4">
               <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-white/5 flex items-center justify-center text-gray-600 dark:text-gray-400">
                     <integration.icon size={24} />
                  </div>
                  <div className="flex-1">
                     <h4 className="text-[15px] font-black mb-1">{integration.title}</h4>
                     <p className="text-[12px] text-gray-500 leading-snug">{integration.desc}</p>
                  </div>
               </div>
               <div className="space-y-2">
                  <div className="flex items-center gap-2">
                     <input 
                        type="password"
                        placeholder={`Enter token`}
                        value={settings?.integrations_json?.[integration.key] || ""}
                        onChange={(e) => {
                           const newIntegrations = { ...(settings?.integrations_json || {}), [integration.key]: e.target.value };
                           setSettings({ ...settings, integrations_json: newIntegrations });
                        }}
                        className="flex-1 bg-white dark:bg-white/[0.03] border border-gray-100 dark:border-white/10 rounded-lg px-3 py-1.5 text-xs text-black dark:text-white"
                     />
                     <button 
                        onClick={() => updateSettings({ integrations_json: settings.integrations_json })}
                        className="p-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors cursor-pointer relative z-10"
                     >
                        <Save size={14} />
                     </button>
                  </div>
                  {settings?.integrations_json?.[integration.key] && (
                     <span className="text-[10px] text-emerald-500 font-bold flex items-center gap-1 uppercase tracking-wider">
                        <Check size={10} /> Saved
                     </span>
                  )}
               </div>
            </div>
          ))}
       </div>
    </div>
  );
}
