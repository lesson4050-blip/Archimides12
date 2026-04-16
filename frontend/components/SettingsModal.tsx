"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, User, Settings, Zap, Calendar, Mail, Shield, 
  Globe, Monitor, Palette, Layers, Cable, Plug,
  ChevronRight, ExternalLink, Moon, Sun, Monitor as MonitorIcon,
  Check, ArrowRight, Plus, Search, Trash2, Edit3, Save, RotateCcw,
  Layout, Cpu, Cloud, Database
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type Section = 
  | "Account" | "Settings" | "Usage" | "Scheduled tasks" 
  | "Mail Cosmo" | "Data controls" | "Cloud browser" | "My Computer" 
  | "Personalization" | "Skills" | "Connectors" | "Integrations";

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeSection, setActiveSection] = useState<Section>("Account");
  const [settings, setSettings] = useState<any>(null);
  const [usageRecords, setUsageRecords] = useState<any[]>([]);
  const [personalizationTab, setPersonalizationTab] = useState<"Profile" | "Knowledge">("Profile");
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      fetchUsage();
    }
  }, [isOpen]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings`);
      if (!res.ok) throw new Error("Backend offline");
      const data = await res.json();
      setSettings(data);
      if (data.theme) applyTheme(data.theme);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch settings", err);
      // Fallback settings for UI demo if backend is offline
      setSettings({
        nickname: "Developer",
        theme: "dark",
        credits_remaining: 300,
        skills_json: {},
        connectors_json: {},
        integrations_json: {}
      });
      setLoading(false);
    }
  };

  const fetchUsage = async () => {
     try {
       const res = await fetch(`${API_BASE}/api/v1/settings/usage`);
       const data = await res.json();
       setUsageRecords(data);
     } catch (err) {
       console.error("Failed to fetch usage", err);
     }
  };

  const updateSettings = async (updates: any) => {
    setIsUpdating("global");
    const prevSettings = { ...settings };
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);

    try {
      const res = await fetch(`${API_BASE}/api/v1/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates)
      });
      const data = await res.json();
      setSettings(data);
      
      if (updates.theme) {
         applyTheme(updates.theme);
      }
    } catch (err) {
      console.error("Failed to update settings", err);
      setSettings(prevSettings);
    } finally {
      setIsUpdating(null);
    }
  };

  const applyTheme = (theme: string) => {
     const html = document.documentElement;
     const body = document.body;
     html.classList.remove("light", "dark");
     body.classList.remove("light", "dark");
     
     let effectiveTheme = theme;
     if (theme === "system") {
        effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
     }
     
     html.classList.add(effectiveTheme);
     body.classList.add(effectiveTheme);
     html.setAttribute("data-theme", effectiveTheme);
     
     // Trigger a custom event for other components
     window.dispatchEvent(new CustomEvent("theme-change", { detail: { theme: effectiveTheme } }));
  };

  const menuItems: { name: Section; icon: any }[] = [
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
  ];

  const connectorMarketplace = [
    { id: "google-search", name: "Google Search", icon: Globe, desc: "Real-time web search and information retrieval." },
    { id: "brave-search", name: "Brave Search", icon: Shield, desc: "Privacy-focused web search engine." },
    { id: "github-mcp", name: "GitHub Repository", icon: Cpu, desc: "Search and read GitHub repositories." },
    { id: "wolfram", name: "Wolfram Alpha", icon: Layout, desc: "Computational intelligence and data analysis." },
    { id: "slack-mcp", name: "Slack Connect", icon: Mail, desc: "Send and receive messages in Slack channels." },
  ];

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-10 pointer-events-auto">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm pointer-events-auto"
        />

        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-6xl h-full max-h-[85vh] bg-[#F9F9F9] dark:bg-[#0F0F0F] rounded-[32px] shadow-2xl overflow-hidden flex border border-gray-200 dark:border-white/5 pointer-events-auto"
        >
           {/* Sidebar */}
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
                     onClick={() => setActiveSection(item.name)}
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

           {/* Content Area */}
           <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#0F0F0F] relative">
              <button 
                onClick={onClose}
                className="absolute top-6 right-8 p-1.5 text-gray-400 hover:text-black dark:hover:text-white transition-colors z-20"
              >
                <X size={20} />
              </button>

              <div className="flex-1 overflow-y-auto p-12 custom-scrollbar pr-12 text-black dark:text-white relative z-10">
                 <div className="max-w-4xl">
                    <h1 className="text-3xl font-extrabold mb-10 tracking-tight">{activeSection}</h1>
                    
                    {activeSection === "Account" && (
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
                    )}

                    {activeSection === "Settings" && (
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
                    )}

                    {activeSection === "Usage" && (
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
                    )}

                    {activeSection === "Personalization" && (
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
                    )}

                    {activeSection === "Scheduled tasks" && (
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
                    )}

                    {activeSection === "Skills" && (
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
                               <button onClick={fetchSettings} className="p-2 bg-gray-100 dark:bg-white/5 rounded-lg text-gray-400 cursor-pointer"><RotateCcw size={16} /></button>
                            </div>
                            <button 
                              onClick={() => {
                                const name = prompt("Enter Skill ID:");
                                if (name) {
                                   const newSkills = { ...(settings?.skills_json || {}), [name]: true };
                                   updateSettings({ skills_json: newSkills });
                                }
                              }}
                              className="flex items-center gap-2 px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-xl text-sm font-black shadow-lg cursor-pointer transition-transform hover:scale-105"
                            >
                               <Plus size={16} /> Add <ChevronRight size={14} />
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
                            )})}
                         </div>
                      </div>
                    )}

                    {activeSection === "Connectors" && (
                      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
                         <h3 className="text-xl font-bold mb-6">Marketplace Gallery</h3>
                         <div className="grid grid-cols-2 gap-6">
                            {connectorMarketplace.map(conn => {
                               const isConnected = !!settings?.connectors_json?.[conn.id];
                               return (
                               <div key={conn.id} className={`p-6 border rounded-2xl flex flex-col gap-4 transition-all ${isConnected ? "border-blue-500 bg-blue-500/[0.02]" : "border-gray-100 dark:border-white/5 bg-white dark:bg-white/[0.02]"}`}>
                                  <div className="flex items-start gap-4">
                                     <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${isConnected ? "bg-blue-500 text-white" : "bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400"}`}>
                                        <conn.icon size={24} />
                                     </div>
                                     <div className="flex-1">
                                        <h4 className="text-[15px] font-black mb-1">{conn.name}</h4>
                                        <p className="text-[12px] text-gray-500 leading-snug line-clamp-2">{conn.desc}</p>
                                     </div>
                                  </div>
                                  <button 
                                    onClick={() => {
                                       const newConn = { ...(settings?.connectors_json || {}), [conn.id]: { command: "npx", args: ["-y", conn.id] } };
                                       updateSettings({ connectors_json: newConn });
                                    }}
                                    disabled={isConnected}
                                    className={`w-full py-2.5 rounded-xl text-xs font-black transition-all cursor-pointer ${
                                       isConnected 
                                       ? "bg-emerald-500/10 text-emerald-500 cursor-default" 
                                       : "bg-black dark:bg-white text-white dark:text-black hover:scale-[1.02] relative z-10"
                                    }`}
                                  >
                                     {isConnected ? (
                                        <span className="flex items-center justify-center gap-2"><Check size={14} /> Connected</span>
                                     ) : "Connect"}
                                  </button>
                               </div>
                            )})}
                         </div>
                      </div>
                    )}

                    {activeSection === "Integrations" && (
                      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
                         <p className="text-sm font-medium text-gray-500 font-bold">Build workflows across your favorite apps</p>
                         <div className="grid grid-cols-2 gap-6">
                            {[
                              { id: "api", title: "Cosmo API", desc: "Build custom integrations.", icon: Cable, key: "api_key" },
                              { id: "zapier", title: "Zapier", desc: "Connect thousands of apps.", icon: Plug, key: "zapier_key" },
                              { id: "slack", title: "Slack", desc: "Assign tasks via @Cosmo in Slack.", icon: Mail, key: "slack_webhook" },
                              { id: "github", title: "GitHub Bot", desc: "Automate your repositories.", icon: Shield, key: "github_token" }
                            ].map(integration => (
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
                    )}

                    {activeSection === "Mail Cosmo" && (
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
                    )}

                    {activeSection === "My Computer" && (
                      <div className="space-y-10 animate-in fade-in slide-in-from-right-2 duration-300">
                         <h3 className="text-2xl font-black mb-8">Access Local Files</h3>
                         <div className="bg-amber-500/5 border border-amber-500/10 p-4 rounded-xl text-amber-500 text-xs font-bold flex items-start gap-3">
                            <Shield size={16} className="shrink-0" />
                            Archimedes will only access the folders you specify below.
                         </div>
                         <button 
                           onClick={async () => {
                              const path = prompt("Enter folder path:");
                              if (path) {
                                 const res = await fetch(`${API_BASE}/api/v1/settings/folders`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ path })
                                 });
                                 if (res.ok) fetchSettings();
                                 else alert("Failed to add folder.");
                              }
                           }}
                           className="px-8 py-3 bg-black dark:bg-white text-white dark:text-black rounded-2xl text-[13px] font-black shadow-lg cursor-pointer transition-transform hover:scale-105"
                         >
                           Add Folder
                         </button>

                         <div className="space-y-4">
                            {settings?.connectors_json?.local_folders?.map((path: string, i: number) => (
                              <div key={i} className="p-4 border border-gray-100 dark:border-white/5 rounded-xl flex items-center justify-between group translate-all hover:border-blue-500/30">
                                 <div className="flex items-center gap-3">
                                    <Monitor size={18} className="text-blue-500" />
                                    <span className="text-[13px] font-medium text-gray-300">{path}</span>
                                 </div>
                                 <button className="text-gray-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"><Trash2 size={16} /></button>
                              </div>
                            ))}
                         </div>
                      </div>
                    )}

                    {activeSection === "Data controls" && (
                      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
                         <div className="flex flex-col gap-6">
                            <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
                               <div>
                                  <h4 className="font-black text-lg">Wipe Browser Session</h4>
                                  <p className="text-sm text-gray-500">Clears cookies, cache and saved logins from the cloud browser.</p>
                               </div>
                               <button 
                                 onClick={async () => {
                                    if(confirm("Confirm cleanup? This cannot be undone.")) {
                                       await fetch(`${API_BASE}/api/v1/settings/cleanup`, { method: "POST" });
                                       alert("Cloud browser is now fresh.");
                                    }
                                 }}
                                 className="px-6 py-2.5 bg-red-500/10 text-red-500 hover:bg-red-500 text-sm font-black rounded-xl transition-all hover:text-white cursor-pointer"
                               >
                                 Fresh Start
                               </button>
                            </div>
                            
                            <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between opacity-40">
                               <div>
                                  <h4 className="font-black text-lg text-gray-300 font-bold">Delete Account</h4>
                                  <p className="text-sm text-gray-500 font-bold">Permanently remove all data and projects.</p>
                               </div>
                               <button disabled className="px-6 py-2.5 bg-gray-100 dark:bg-white/5 text-gray-400 text-sm font-black rounded-xl">
                                 Request Deletion
                               </button>
                            </div>
                         </div>
                      </div>
                    )}

                    {activeSection === "Cloud browser" && (
                      <div className="space-y-8 animate-in fade-in slide-in-from-right-2 duration-300">
                         <div className="flex flex-col gap-6">
                            <div className="p-8 bg-blue-500/[0.03] border border-blue-500/10 rounded-3xl flex items-start gap-6">
                               <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
                                  <Globe size={32} />
                               </div>
                               <div className="flex-1 pt-1">
                                  <h4 className="font-black text-xl mb-2 text-black dark:text-white">Long-term Session</h4>
                                  <p className="text-sm text-gray-500 mb-6 font-bold leading-relaxed">By default, Archimedes keeps browser data for up to 30 days. Disable this if you prefer anonymous, fresh browser windows for every task.</p>
                                  <button 
                                    onClick={() => updateSettings({ browser_persistence: !settings?.browser_persistence })}
                                    className={`w-14 h-7 rounded-full transition-colors relative cursor-pointer ${settings?.browser_persistence ? "bg-blue-500" : "bg-gray-300 dark:bg-white/10"}`}
                                  >
                                     <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all shadow-md ${settings?.browser_persistence ? "left-8" : "left-1"}`} />
                                  </button>
                               </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4">
                               <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
                                  <h4 className="font-black text-black dark:text-white">Current Region</h4>
                                  <span className="px-3 py-1 bg-gray-100 dark:bg-white/5 rounded-lg text-xs font-black tracking-widest uppercase text-black dark:text-white">Oregon (USA)</span>
                               </div>
                               <div className="p-6 border border-gray-100 dark:border-white/5 rounded-2xl flex items-center justify-between">
                                  <h4 className="font-black text-black dark:text-white">Concurrency</h4>
                                  <span className="px-3 py-1 bg-gray-100 dark:bg-white/5 rounded-lg text-xs font-black tracking-widest uppercase text-black dark:text-white">Up to 3 tabs</span>
                               </div>
                            </div>
                         </div>
                      </div>
                    )}
                 </div>
              </div>
           </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
