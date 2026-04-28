"use client";

import { Mail, Edit3, Plus, Trash2 } from "lucide-react";

export default function MailCosmoSection() {
  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-right-2 duration-300">
      <div className="p-10 bg-blue-500/[0.03] dark:bg-blue-500/[0.05] rounded-3xl border border-blue-500/10 flex flex-col items-center text-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-blue-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/20">
          <Mail size={32} />
        </div>
        <h3 className="text-xl font-black">Enable Mail Tasks</h3>
        <p className="text-sm text-gray-500 max-w-sm">Create tasks by sending emails to Cosmo. Simply CC our bot to start collaborative work.</p>
        <button className="px-8 py-2.5 bg-black dark:bg-white text-white dark:text-black rounded-xl text-sm font-bold shadow-lg hover:scale-105 transition-all">Get Started</button>
      </div>

      <section className="space-y-6">
        <h3 className="text-[15px] font-black border-b border-gray-100 dark:border-white/5 pb-2">Bot Settings</h3>
        <div>
          <label className="block text-[13px] font-bold text-gray-700 dark:text-gray-300 mb-1">Cosmo&apos;s email</label>
          <div className="flex items-center gap-2 text-black dark:text-white">
            <input readOnly value="archimedes-cosmo@cosmo.bot" className="flex-1 bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 rounded-lg px-3 py-2 text-sm text-gray-500" />
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-white/5 rounded-lg transition-colors"><Edit3 size={16} className="text-gray-400" /></button>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[15px] font-black">Approved senders</h3>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 rounded-lg text-[11px] font-black transition-colors cursor-pointer">
            <Plus size={14} /> Add sender
          </button>
        </div>
        <div className="p-4 border border-gray-100 dark:border-white/5 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-teal-600/10 flex items-center justify-center text-teal-600">
              <Mail size={16} />
            </div>
            <span className="text-[13px] font-medium text-gray-300">developer@cosmo.ai</span>
          </div>
          <button className="text-gray-400 hover:text-red-500 transition-colors cursor-pointer"><Trash2 size={16} /></button>
        </div>
      </section>
    </div>
  );
}
