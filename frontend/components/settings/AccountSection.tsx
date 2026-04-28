"use client";

import { useSettingsStore } from "@/lib/settingsStore";
import { Layers, ArrowRight, Zap, Calendar } from "lucide-react";

export default function AccountSection({ onClose }: { onClose: () => void }) {
  const { settings } = useSettingsStore();

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
       <div className="flex items-center gap-6 p-1 py-4">
          <div className="w-20 h-20 rounded-full bg-blue-600 flex items-center justify-center text-4xl font-bold text-white shadow-lg">
            {settings?.nickname?.[0] || "D"}
          </div>
          <div className="flex-1">
             <h2 className="text-xl font-bold">{settings?.nickname || "Developer"}</h2>
             <p className="text-gray-500 font-medium">dev@cosmo.ai</p>
          </div>
          <div className="flex gap-2">
             <button className="p-2 border border-gray-200 dark:border-white/10 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                <Layers size={18} className="text-gray-600 dark:text-gray-400" />
             </button>
             <button 
               className="p-2 border border-gray-200 dark:border-white/10 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/10 text-red-500 transition-colors"
               onClick={onClose}
             >
                <ArrowRight size={18} />
             </button>
          </div>
       </div>

       <div className="bg-gray-50 dark:bg-white/5 rounded-2xl p-6 border border-gray-100 dark:border-white/5">
          <div className="flex items-center justify-between mb-6">
             <h3 className="text-lg font-bold">Free</h3>
             <button className="px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-bold shadow-lg hover:scale-105 transition-transform">
               Upgrade
             </button>
          </div>
          <div className="space-y-4">
             <div className="flex items-center justify-between text-sm py-2 border-b border-gray-200/50 dark:border-white/5">
                <div className="flex items-center gap-2 font-bold text-gray-700 dark:text-gray-300">
                   <Zap size={14} className="text-blue-500" />
                   Credits
                </div>
                <span className="font-bold">{settings?.credits_remaining || 0}</span>
             </div>
             <div className="flex items-center justify-between text-sm py-2">
                <div className="flex items-center gap-2 font-bold text-gray-700 dark:text-gray-300">
                   <Calendar size={14} className="text-gray-400" />
                   Daily refresh credits
                </div>
                <span className="font-bold">300</span>
             </div>
          </div>
       </div>
    </div>
  );
}
