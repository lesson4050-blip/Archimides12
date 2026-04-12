"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, Layout, LayoutGrid, User, Briefcase, Cloud, Plus, ExternalLink } from "lucide-react";
import Image from "next/image";
import { AgentMode } from "@/lib/modes";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  layout: <Layout size={16} />,
  grid: <LayoutGrid size={16} />,
  user: <User size={16} />,
  briefcase: <Briefcase size={16} />,
  cloud: <Cloud size={16} />,
};

interface ModeDiscoveryProps {
  mode: AgentMode;
  onSelectPrompt: (prompt: string) => void;
  onSelectTemplate?: (template: string) => void;
}

export default function ModeDiscovery({ mode, onSelectPrompt, onSelectTemplate }: ModeDiscoveryProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-3xl mt-8 flex flex-col gap-10 pb-20"
    >
      {/* Sample Prompts Section */}
      <section>
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 ml-1">
          Sample prompts
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {mode.quickPrompts.map((prompt, i) => (
            <motion.button
              key={i}
              whileHover={{ y: -2, backgroundColor: "#1A1A1A", borderColor: "#333" }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectPrompt(prompt)}
              className="flex items-start justify-between p-4 rounded-2xl bg-[#141414] border border-[#222] transition-all group text-left"
            >
              <span className="text-sm text-gray-400 group-hover:text-gray-200 font-medium leading-normal">
                {prompt}
              </span>
              <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 opacity-40 group-hover:opacity-100 group-hover:bg-blue-600/10 group-hover:text-blue-400 transition-all">
                <ArrowUpRight size={14} />
              </div>
            </motion.button>
          ))}
        </div>
      </section>

      {/* Mode Specific Section: Slides Templates */}
      {mode.id === "slides" && mode.templates && (
        <section>
          <div className="flex items-center justify-between mb-4 ml-1">
            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
              Choose a template
            </h3>
            <div className="flex items-center gap-2 bg-[#1A1A1A] border border-[#333] px-3 py-1.5 rounded-xl cursor-not-allowed opacity-60">
                <span className="text-[10px] font-bold text-gray-400">📋 8 - 12</span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
             {/* Import template placeholder */}
             <motion.button
                whileHover={{ scale: 1.02 }}
                className="aspect-video rounded-2xl border-2 border-dashed border-[#222] flex flex-col items-center justify-center gap-2 hover:border-[#333] hover:bg-[#111] transition-all"
             >
                <div className="w-10 h-10 rounded-full bg-[#1A1A1A] flex items-center justify-center text-gray-500">
                    <Plus size={20} />
                </div>
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Import template</span>
             </motion.button>

             {mode.templates.map((tpl, i) => (
               <motion.button
                 key={i}
                 whileHover={{ scale: 1.02, y: -4 }}
                 onClick={() => onSelectTemplate?.(tpl.name)}
                 className="flex flex-col gap-2 group text-left"
               >
                 <div className="relative aspect-video rounded-2xl overflow-hidden border border-[#222] group-hover:border-blue-500/50 transition-all">
                    <Image 
                      src={tpl.image} 
                      alt={tpl.name} 
                      fill 
                      className="object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                 </div>
                 <div className="flex items-center gap-1.5 ml-1">
                    <span className="text-[11px] font-bold text-gray-300 tracking-wide">{tpl.name}</span>
                    <span className="text-[11px] grayscale opacity-60 group-hover:grayscale-0 group-hover:opacity-100 transition-all">{tpl.emoji}</span>
                 </div>
               </motion.button>
             ))}
          </div>
        </section>
      )}

      {/* Mode Specific Section: Website Categories */}
      {mode.id === "website" && mode.categories && (
        <section>
          <div className="flex items-center justify-between mb-4 ml-1">
            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
              What would you like to build?
            </h3>
            <div className="flex items-center gap-4">
                <button className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 hover:text-gray-300 transition-colors uppercase tracking-wider">
                    <ExternalLink size={12} /> Add website reference
                </button>
                <button className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 hover:text-gray-300 transition-colors uppercase tracking-wider">
                    🖼️ Import from Figma
                </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
             {mode.categories.map((cat, i) => (
               <motion.button
                 key={i}
                 whileHover={{ y: -2, backgroundColor: "#1A1A1A" }}
                 whileTap={{ scale: 0.98 }}
                 className="flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-[#141414] border border-[#222] hover:border-[#333] transition-all group"
               >
                 <span className="text-gray-500 group-hover:text-gray-300 transition-colors">
                    {CATEGORY_ICONS[cat.icon]}
                 </span>
                 <span className="text-[11px] font-bold text-gray-400 group-hover:text-gray-200 uppercase tracking-wider">
                    {cat.label}
                 </span>
               </motion.button>
             ))}
             <motion.button className="w-10 h-10 rounded-2xl bg-[#141414] border border-[#222] flex items-center justify-center text-gray-500 hover:bg-[#1A1A1A] transition-all">
                <ArrowUpRight size={16} />
             </motion.button>
          </div>

          {/* Integrations Footer (Simulation) */}
          <div className="mt-20 p-6 rounded-3xl bg-gradient-to-br from-[#121212] to-[#0A0A0A] border border-[#1A1A1A] flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                    Powerful built-in Integrations <ArrowUpRight size={12} />
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                  {["LLM", "Stripe integration", "Database", "Image generation", "Maps", "Notification", "File storage", "Data API", "Voice-to-Text"].map(tag => (
                      <span key={tag} className="px-3 py-1.5 rounded-xl bg-[#1A1A1A] border border-[#222] text-[10px] font-bold text-gray-600 uppercase tracking-wider">
                          {tag}
                      </span>
                  ))}
              </div>
          </div>
        </section>
      )}
    </motion.div>
  );
}
