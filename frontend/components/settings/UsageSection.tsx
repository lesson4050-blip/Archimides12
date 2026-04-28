"use client";

import { useSettingsStore } from "@/lib/settingsStore";

export default function UsageSection() {
  const { settings, usageRecords } = useSettingsStore();

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-right-2 duration-300">
       <div className="bg-gray-50 dark:bg-white/5 rounded-2xl p-8 border border-gray-100 dark:border-white/5">
          <div className="flex items-baseline gap-4 mb-2">
             <span className="text-4xl font-black">Free</span>
             <button className="px-4 py-1.5 bg-black dark:bg-white text-white dark:text-black rounded-lg text-xs font-black shadow-lg">
               Upgrade
             </button>
          </div>
          <div className="flex gap-8 mt-6">
             <div>
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Credits</p>
                <p className="text-xl font-black">{settings?.credits_remaining || 0}</p>
             </div>
             <div>
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Daily refresh</p>
                <p className="text-xl font-black">300</p>
             </div>
          </div>
       </div>
       
       <div>
          <h3 className="text-lg font-bold mb-6">Usage history</h3>
          <div className="w-full overflow-hidden border border-gray-100 dark:border-white/5 rounded-2xl">
             <table className="w-full text-left border-collapse backdrop-blur-md">
                <thead className="bg-gray-50 dark:bg-white/5 text-[11px] font-bold text-gray-400 uppercase tracking-widest text-black dark:text-white">
                   <tr>
                      <th className="px-6 py-4">Details</th>
                      <th className="px-6 py-4">Date</th>
                      <th className="px-6 py-4 text-right">Change</th>
                   </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-white/5 text-[13px] font-medium text-black dark:text-white">
                   {usageRecords.length > 0 ? usageRecords.map((record, i) => (
                     <tr key={i} className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4 dark:text-gray-200">{record.details}</td>
                        <td className="px-6 py-4 text-gray-500">{new Date(record.created_at).toLocaleDateString()}</td>
                        <td className={`px-6 py-4 text-right font-bold ${record.credits_change > 0 ? "text-emerald-500" : "text-gray-700 dark:text-gray-300"}`}>
                           {record.credits_change > 0 ? `+${record.credits_change}` : record.credits_change}
                        </td>
                     </tr>
                   )) : (
                     <tr>
                        <td colSpan={3} className="px-6 py-10 text-center text-gray-500 italic">No records found</td>
                     </tr>
                   )}
                </tbody>
             </table>
          </div>
       </div>
    </div>
  );
}
