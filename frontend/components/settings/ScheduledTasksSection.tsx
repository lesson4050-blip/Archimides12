"use client";

export default function ScheduledTasksSection() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
      <div className="flex gap-4">
        <div className="bg-gray-100 dark:bg-white/5 p-1 rounded-xl flex">
          <button className="px-4 py-1.5 rounded-lg text-sm font-bold bg-white dark:bg-white/10 shadow-sm cursor-pointer">Scheduled</button>
          <button className="px-4 py-1.5 rounded-lg text-sm font-bold text-gray-500 hover:text-black dark:hover:text-gray-300 transition-colors cursor-pointer">Completed</button>
        </div>
      </div>

      <div className="w-full border border-gray-100 dark:border-white/5 rounded-2xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 dark:bg-white/5 text-[11px] font-bold text-gray-400 uppercase tracking-widest border-b dark:border-white/5 text-black dark:text-white">
            <tr>
              <th className="px-6 py-4">Title</th>
              <th className="px-6 py-4">Schedule at</th>
              <th className="px-6 py-4">Status</th>
            </tr>
          </thead>
          <tbody className="text-black dark:text-white">
            <tr className="border-b dark:border-white/5">
              <td className="px-6 py-4 font-bold">Live Task Monitor</td>
              <td className="px-6 py-4 text-gray-500 text-sm">Every 1h</td>
              <td className="px-6 py-4"><span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[10px] font-black uppercase rounded">Active</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
