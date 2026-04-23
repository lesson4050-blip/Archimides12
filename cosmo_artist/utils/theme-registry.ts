export interface ThemeVariables {
  '--bg-primary': string;
  '--bg-secondary'?: string;
  '--text-primary': string;
  '--text-secondary': string;
  '--accent-primary': string;
  '--accent-secondary'?: string;
  '--border-primary': string;
  '--glass-bg'?: string;
  '--glass-border'?: string;
  '--font-main': string;
}

export const THEME_REGISTRY: Record<string, ThemeVariables> = {
  midnight_glass: {
    '--bg-primary': '#020617', // Deep Navy/Black
    '--bg-secondary': '#0f172a',
    '--text-primary': '#f8fafc',
    '--text-secondary': '#94a3b8',
    '--accent-primary': '#6366f1', // Indigo 500
    '--accent-secondary': '#f43f5e', // Rose 500
    '--border-primary': 'rgba(99, 102, 241, 0.2)',
    '--glass-bg': 'rgba(15, 23, 42, 0.7)',
    '--glass-border': 'rgba(255, 255, 255, 0.08)',
    '--font-main': 'var(--font-syne), sans-serif',
  },
  midnight_obsidian: {
    '--bg-primary': '#000000',
    '--bg-secondary': '#0a0a0a',
    '--text-primary': '#ffffff',
    '--text-secondary': '#a1a1aa',
    '--accent-primary': '#fbbf24', // Amber 400 (Gold)
    '--accent-secondary': '#ffffff',
    '--border-primary': 'rgba(251, 191, 36, 0.3)',
    '--glass-bg': 'rgba(0, 0, 0, 0.8)',
    '--glass-border': 'rgba(251, 191, 36, 0.2)',
    '--font-main': 'var(--font-unbounded), sans-serif',
  },
  clean_editorial: {
    '--bg-primary': '#ffffff',
    '--bg-secondary': '#f8f9fa',
    '--text-primary': '#000000',
    '--text-secondary': '#404040',
    '--accent-primary': '#000000',
    '--accent-secondary': '#6366f1',
    '--border-primary': '#e5e5e5',
    '--font-main': 'var(--font-unbounded), sans-serif',
  },
  warm_minimal: {
    '--bg-primary': '#fdfcf7', // Off-white/Cream
    '--bg-secondary': '#f9f6ee',
    '--text-primary': '#1a1a1a',
    '--text-secondary': '#525252',
    '--accent-primary': '#7c2d12', // Warm brown
    '--accent-secondary': '#fb923c', // Orange
    '--border-primary': '#e5e7eb',
    '--font-main': 'var(--font-inter), sans-serif',
  },
  industrial_brutalist: {
    '--bg-primary': '#111111',
    '--bg-secondary': '#1a1a1a',
    '--text-primary': '#ffffff',
    '--text-secondary': '#888888',
    '--accent-primary': '#ff4d00', // Safety Orange
    '--accent-secondary': '#00ff00', // Matrix Green
    '--border-primary': '#333333',
    '--glass-bg': 'rgba(20, 20, 20, 0.9)',
    '--glass-border': '#ff4d00',
    '--font-main': 'var(--font-unbounded), monospace',
  },
  arctic_minimal: {
    '--bg-primary': '#f0f4f8',
    '--bg-secondary': '#ffffff',
    '--text-primary': '#0f172a',
    '--text-secondary': '#64748b',
    '--accent-primary': '#38bdf8', // Sky 400
    '--accent-secondary': '#818cf8', // Indigo 400
    '--border-primary': '#e2e8f0',
    '--font-main': 'var(--font-inter), sans-serif',
  }
};

export const getThemeVariables = (paletteName?: string): ThemeVariables => {
  return THEME_REGISTRY[paletteName || ''] || THEME_REGISTRY.slate_professional;
};
