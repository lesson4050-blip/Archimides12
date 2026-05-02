import { create } from 'zustand';
import { ArtifactData } from '@/components/ArtifactViewer';

export interface Message {
  role: "user" | "assistant" | "system";
  type: "text" | "info" | "ask" | "result" | "plan" | "artifact" | "thought" | "tool" | "tool_call" | "file_download";
  content: string;
  artifactData?: ArtifactData;
  filename?: string;
  download_url?: string;
  size_kb?: number;
  preview_url?: string;
}

interface AppState {
  // Chat State
  messages: Message[];
  input: string;
  isWorking: boolean;
  isListening: boolean;
  webSearchEnabled: boolean;
  globeEnabled: boolean;
  
  // Artifact State
  artifacts: ArtifactData[];
  viewingArtifact: ArtifactData | null;
  hasToolEvents: boolean;
  
  // Settings & Modes
  activeMode: string | null;
  
  // Header State
  showUpdateModal: boolean;
  isCheckingUpdate: boolean;
  showSettingsModal: boolean;
  
  // Task state
  taskStartTime: number | null;
  taskElapsed: number;
  suggestions: string[];
  confidence: {score: number; label: string} | null;
  liveReasoning: string;

  // Actions
  setMessages: (updater: Message[] | ((prev: Message[]) => Message[])) => void;
  setInput: (val: string | ((prev: string) => string)) => void;
  setIsWorking: (val: boolean) => void;
  setIsListening: (val: boolean) => void;
  setWebSearchEnabled: (val: boolean) => void;
  setGlobeEnabled: (val: boolean) => void;
  setArtifacts: (updater: ArtifactData[] | ((prev: ArtifactData[]) => ArtifactData[])) => void;
  setViewingArtifact: (val: ArtifactData | null) => void;
  setHasToolEvents: (val: boolean) => void;
  setActiveMode: (val: string | null) => void;
  
  setShowUpdateModal: (val: boolean) => void;
  setIsCheckingUpdate: (val: boolean) => void;
  setShowSettingsModal: (val: boolean) => void;
  
  setTaskStartTime: (val: number | null) => void;
  setTaskElapsed: (val: number) => void;
  setSuggestions: (val: string[]) => void;
  setConfidence: (val: {score: number; label: string} | null) => void;
  setLiveReasoning: (updater: string | ((prev: string) => string)) => void;
}

export const useAppStore = create<AppState>((set) => ({
  messages: [],
  input: "",
  isWorking: false,
  isListening: false,
  webSearchEnabled: false,
  globeEnabled: false,
  artifacts: [],
  viewingArtifact: null,
  hasToolEvents: false,
  activeMode: null,
  showUpdateModal: false,
  isCheckingUpdate: false,
  showSettingsModal: false,
  taskStartTime: null,
  taskElapsed: 0,
  suggestions: [],
  confidence: null,
  liveReasoning: "",

  setMessages: (updater) => set((state) => ({ 
      messages: typeof updater === 'function' ? updater(state.messages) : updater 
  })),
  setInput: (updater) => set((state) => ({ 
      input: typeof updater === 'function' ? updater(state.input) : updater 
  })),
  setIsWorking: (val) => set({ isWorking: val }),
  setIsListening: (val) => set({ isListening: val }),
  setWebSearchEnabled: (val) => set({ webSearchEnabled: val }),
  setGlobeEnabled: (val) => set({ globeEnabled: val }),
  setArtifacts: (updater) => set((state) => ({ 
      artifacts: typeof updater === 'function' ? updater(state.artifacts) : updater 
  })),
  setViewingArtifact: (val) => set({ viewingArtifact: val }),
  setHasToolEvents: (val) => set({ hasToolEvents: val }),
  setActiveMode: (val) => set({ activeMode: val }),
  setShowUpdateModal: (val) => set({ showUpdateModal: val }),
  setIsCheckingUpdate: (val) => set({ isCheckingUpdate: val }),
  setShowSettingsModal: (val) => set({ showSettingsModal: val }),
  setTaskStartTime: (val) => set({ taskStartTime: val }),
  setTaskElapsed: (val) => set({ taskElapsed: val }),
  setSuggestions: (val) => set({ suggestions: val }),
  setConfidence: (val) => set({ confidence: val }),
  setLiveReasoning: (updater) => set((state) => ({ 
      liveReasoning: typeof updater === 'function' ? updater(state.liveReasoning) : updater 
  })),
}));
