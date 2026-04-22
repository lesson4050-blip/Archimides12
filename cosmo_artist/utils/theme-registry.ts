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
    '--bg-primary': '#030712', // Slate 950
    '--bg-secondary': '#111827', // Slate 900
    '--text-primary': '#f9fafb', // Gray 50
    '--text-secondary': '#9ca3af', // Gray 400
    '--accent-primary': '#8b5cf6', // Violet 500
    '--accent-secondary': '#ec4899', // Pink 500
    '--border-primary': 'rgba(139, 92, 246, 0.3)',
    '--glass-bg': 'rgba(17, 24, 39, 0.7)',
    '--glass-border': 'rgba(255, 255, 255, 0.1)',
    '--font-main': 'var(--font-syne), sans-serif',
  },
  warm_minimal: {
    '--bg-primary': '#fffaf5', // Cream
    '--bg-secondary': '#fff1e2', 
    '--text-primary': '#451a03', // Amber 950
    '--text-secondary': '#92400e', // Amber 800
    '--accent-primary': '#d97706', // Amber 600
    '--border-primary': '#fde68a',
    '--font-main': 'var(--font-inter), sans-serif',
  },
  clean_editorial: {
    '--bg-primary': '#ffffff',
    '--bg-secondary': '#f9fafb',
    '--text-primary': '#111827',
    '--text-secondary': '#4b5563',
    '--accent-primary': '#000000',
    '--border-primary': '#e5e7eb',
    '--font-main': 'var(--font-unbounded), sans-serif',
  },
  slate_professional: {
    '--bg-primary': '#f8fafc',
    '--bg-secondary': '#f1f5f9',
    '--text-primary': '#0f172a',
    '--text-secondary': '#475569',
    '--accent-primary': '#2563eb', // Blue 600
    '--border-primary': '#cbd5e1',
    '--font-main': 'var(--font-inter), sans-serif',
  },
  cyber_neon: {
    '--bg-primary': '#000000',
    '--bg-secondary': '#050505',
    '--text-primary': '#ffffff',
    '--text-secondary': '#a3a3a3',
    '--accent-primary': '#22c55e', // Green 500
    '--accent-secondary': '#ef4444', // Red 500
    '--border-primary': '#16a34a',
    '--font-main': 'var(--font-syne), monospace',
  }
};

export const getThemeVariables = (paletteName?: string): ThemeVariables => {
  return THEME_REGISTRY[paletteName || ''] || THEME_REGISTRY.slate_professional;
};
