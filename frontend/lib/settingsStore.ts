import { create } from 'zustand';

export type Section = 
  | "Account" | "Settings" | "Usage" | "Scheduled tasks" 
  | "Mail Cosmo" | "Data controls" | "Cloud browser" | "My Computer" 
  | "Personalization" | "Skills" | "Connectors" | "Integrations";

interface SettingsState {
  activeSection: Section;
  settings: any;
  usageRecords: any[];
  personalizationTab: "Profile" | "Knowledge";
  loading: boolean;
  isUpdating: string | null;

  setActiveSection: (s: Section) => void;
  setSettings: (s: any) => void;
  setUsageRecords: (r: any[]) => void;
  setPersonalizationTab: (t: "Profile" | "Knowledge") => void;
  setLoading: (l: boolean) => void;
  setIsUpdating: (u: string | null) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  activeSection: "Account",
  settings: null,
  usageRecords: [],
  personalizationTab: "Profile",
  loading: true,
  isUpdating: null,
  setActiveSection: (s) => set({ activeSection: s }),
  setSettings: (s) => set({ settings: s }),
  setUsageRecords: (r) => set({ usageRecords: r }),
  setPersonalizationTab: (t) => set({ personalizationTab: t }),
  setLoading: (l) => set({ loading: l }),
  setIsUpdating: (u) => set({ isUpdating: u }),
}));
