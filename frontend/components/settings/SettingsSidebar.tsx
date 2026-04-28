"use client";

import { useSettingsStore } from "@/lib/settingsStore";
import { 
  User, Settings, Zap, Calendar, Mail, Shield, 
  Globe, Monitor, Palette, Layers, Cable, Plug,
  RotateCcw, ExternalLink
} from "lucide-react";

const menuItems = [
  { name: "Account", icon: User },
  { name: "Settings", icon: Settings },
  { name: "Usage", icon: Zap },
  { name: "Scheduled tasks", icon: Calendar },
  { name: "Mail Cosmo", icon: Mail },
  { name: "Data controls", icon: Shield },
  { name: "Cloud browser", icon: Globe },
  { name: "My Computer", icon: Monitor },
  { name: "Personalization", icon: Palette },
  { name: "Skills", icon: Layers },
  { name: "Connectors", icon: Cable },
  { name: "Integrations", icon: Plug },
] as const;

export default function SettingsSidebar({ fetchSettings }: { fetchSettings: () => void }) {
  const { activeSection, setActiveSection, settings, isUpdating } = useSettingsStore();

  return (
    <div className="w-72 border-r border-gray-200 dark:border-white/5 flex flex-col p-6 bg-[#F3F3F3] dark:bg-[#141414] shrink-0">
      <div className="flex items-center gap-3 px-3 py-2 mb-8 bg-white dark:bg-white/5 rounded-xl border border-gray-100 dark:border-white/5 shadow-sm">
         <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
            {settings?.nickname?.[0] || "D"}
         </div>
         <div className="flex flex-col">
            <span className="text-[13px] font-bold dark:text-gray-100">{settings?.nickname || "Developer"}</span>
            <span className="text-[11px] text-gray-500 font-medium">Personal</span>
         </div>
         <RotateCcw 
            size={12} 
            className={`ml-auto text-gray-400 cursor-pointer hover:rotate-180 transition-transform duration-500 ${isUpdating ? "animate-spin" : ""}`} 
            onClick={fetchSettings} 
         />
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto custom-scrollbar pr-2">
         {menuItems.map((item) => (
           <button
             key={item.name}
             onClick={() => setActiveSection(item.name as any)}
             className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-bold transition-all relative z-10 ${
               activeSection === item.name 
                 ? "bg-white dark:bg-white/10 text-black dark:text-white shadow-sm ring-1 ring-black/5 dark:ring-white/5" 
                 : "text-gray-500 hover:text-black dark:hover:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-white/5"
             }`}
           >
             <item.icon size={16} className={activeSection === item.name ? "text-blue-500" : "text-gray-400"} />
             <span className="truncate">{item.name}</span>
           </button>
         ))}
      </nav>

      <div className="mt-8 pt-6 border-t border-gray-200 dark:border-white/5">
         <button className="w-full flex items-center gap-3 px-4 py-2 text-[13px] font-bold text-gray-500 hover:text-black dark:hover:text-gray-200 transition-colors">
            <Globe size={16} className="text-gray-400" />
            Get help
            <ExternalLink size={12} className="ml-auto opacity-40" />
         </button>
      </div>
    </div>
  );
}
