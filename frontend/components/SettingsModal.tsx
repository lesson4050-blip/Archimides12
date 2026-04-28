"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useSettingsStore } from "@/lib/settingsStore";
import { useSettings } from "@/hooks/useSettings";

import SettingsSidebar from "./settings/SettingsSidebar";
import AccountSection from "./settings/AccountSection";
import UsageSection from "./settings/UsageSection";
import PersonalizationSection from "./settings/PersonalizationSection";
import IntegrationsSection from "./settings/IntegrationsSection";

// New modular sections
import GeneralSettingsSection from "./settings/GeneralSettingsSection";
import SkillsSection from "./settings/SkillsSection";
import ConnectorsSection from "./settings/ConnectorsSection";
import ScheduledTasksSection from "./settings/ScheduledTasksSection";
import MailCosmoSection from "./settings/MailCosmoSection";
import SystemSection from "./settings/SystemSection";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { activeSection } = useSettingsStore();
  const { updateSettings, fetchSettings } = useSettings(isOpen);

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
           <SettingsSidebar fetchSettings={fetchSettings} />

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
                    
                    {activeSection === "Account" && <AccountSection onClose={onClose} />}
                    
                    {activeSection === "Usage" && <UsageSection />}
                    
                    {activeSection === "Personalization" && <PersonalizationSection updateSettings={updateSettings} onClose={onClose} />}
                    
                    {activeSection === "Integrations" && <IntegrationsSection updateSettings={updateSettings} />}

                    {activeSection === "Settings" && <GeneralSettingsSection updateSettings={updateSettings} />}

                    {activeSection === "Skills" && <SkillsSection updateSettings={updateSettings} fetchSettings={fetchSettings} />}

                    {activeSection === "Connectors" && <ConnectorsSection updateSettings={updateSettings} />}

                    {activeSection === "Scheduled tasks" && <ScheduledTasksSection />}

                    {activeSection === "Mail Cosmo" && <MailCosmoSection />}

                    {(activeSection === "My Computer" || activeSection === "Data controls" || activeSection === "Cloud browser") && (
                      <SystemSection activeSection={activeSection} updateSettings={updateSettings} fetchSettings={fetchSettings} />
                    )}
                 </div>
              </div>
           </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
