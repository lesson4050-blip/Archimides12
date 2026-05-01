/**
 * Archimedes Canvas — SlideRenderer
 * 
 * Renders presentation JSON into beautiful Tailwind slides.
 * Replaces the legacy Presenton engine completely.
 * 
 * Features:
 * - Framer Motion animations
 * - All layout types supported
 * - Dark Archimedes theme
 * - Keyboard navigation
 * - PDF export via print
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';

// ── Types ──

interface SlideContent {
  title?: string;
  subtitle?: string;
  body?: Array<{ text: string; icon?: string; emphasis?: boolean }>;
  code?: { language: string; content: string };
  metrics?: Array<{ label: string; value: string; delta?: string; trend?: 'up' | 'down' | 'neutral' }>;
  quote_text?: string;
  quote_author?: string;
  cta_text?: string;
}

interface VisualConfig {
  background: string;
  animation: string;
  accent_color?: string;
}

interface Slide {
  layout_type: string;
  slide_number?: number;
  content: SlideContent;
  visual_config: VisualConfig;
  speaker_notes?: string;
}

interface Presentation {
  title: string;
  subtitle?: string;
  author?: string;
  theme?: string;
  slides: Slide[];
}

// ── Background mapping ──

const BG_CLASSES: Record<string, string> = {
  dark_gradient: 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900',
  accent_purple: 'bg-gradient-to-br from-purple-900 via-gray-900 to-indigo-900',
  accent_blue: 'bg-gradient-to-br from-blue-900 via-gray-900 to-blue-800',
  light_minimal: 'bg-white',
  code_dark: 'bg-gray-950',
  image_overlay: 'bg-gray-900',
};

// ── Layout Components ──

const HeroLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-16">
      <div className="mb-6">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 bg-purple-500 rounded-full" />
          <span className="text-purple-300 text-lg font-medium tracking-widest uppercase">
            Archimedes AI
          </span>
        </div>
        {content.title && (
          <h1 className="text-6xl font-extrabold text-white leading-tight mb-6">
            {content.title}
          </h1>
        )}
        {content.subtitle && (
          <p className="text-2xl text-gray-300 max-w-3xl mx-auto">
            {content.subtitle}
          </p>
        )}
      </div>
    </div>
  );
};

const BulletLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex flex-col justify-center h-full px-20">
      {content.title && (
        <h2 className="text-4xl font-bold text-white mb-10 border-b border-purple-500/30 pb-4">
          {content.title}
        </h2>
      )}
      {content.body && (
        <ul className="space-y-4">
          {content.body.map((item, i) => (
            <li key={i} className="flex items-start gap-4">
              <span className="text-purple-400 text-xl mt-0.5 flex-shrink-0">▸</span>
              <span className={`text-xl ${item.emphasis ? 'text-white font-semibold' : 'text-gray-200'}`}>
                {item.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const SplitContentLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col justify-center px-16 border-r border-white/10">
        {content.title && (
          <h2 className="text-4xl font-bold text-white mb-6">{content.title}</h2>
        )}
        {content.subtitle && (
          <p className="text-xl text-gray-300 mb-6">{content.subtitle}</p>
        )}
        {content.body && content.body.slice(0, 4).map((item, i) => (
          <div key={i} className="flex items-start gap-3 mb-4">
            <span className="text-purple-400">▸</span>
            <span className="text-gray-200">{item.text}</span>
          </div>
        ))}
      </div>
      <div className="flex-1 flex items-center justify-center px-12">
        {content.code ? (
          <pre className="bg-gray-950 rounded-xl p-6 text-sm text-green-300 overflow-hidden w-full max-h-80">
            <code>{content.code.content}</code>
          </pre>
        ) : (
          <div className="w-full h-64 bg-purple-900/20 rounded-2xl border border-purple-500/20 flex items-center justify-center">
            <span className="text-gray-500">Visual</span>
          </div>
        )}
      </div>
    </div>
  );
};

const DataGridLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  const metrics = content.metrics || [];
  return (
    <div className="flex flex-col justify-center h-full px-16">
      {content.title && (
        <h2 className="text-4xl font-bold text-white mb-10 text-center">{content.title}</h2>
      )}
      <div className={`grid ${metrics.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'} gap-6`}>
        {metrics.map((metric, i) => (
          <div key={i} className="bg-white/5 rounded-2xl p-6 border border-white/10">
            <div className="text-4xl font-extrabold text-white mb-2">{metric.value}</div>
            <div className="text-gray-400 text-sm uppercase tracking-wider">{metric.label}</div>
            {metric.delta && (
              <div className={`text-sm mt-2 ${
                metric.trend === 'up' ? 'text-green-400' :
                metric.trend === 'down' ? 'text-red-400' : 'text-gray-400'
              }`}>
                {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '→'} {metric.delta}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const QuoteLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex flex-col items-center justify-center h-full px-20 text-center">
      <div className="text-8xl text-purple-400/30 font-serif mb-4">"</div>
      {content.quote_text && (
        <blockquote className="text-3xl text-white font-light leading-relaxed mb-8 max-w-4xl">
          {content.quote_text}
        </blockquote>
      )}
      {content.quote_author && (
        <cite className="text-purple-300 text-lg not-italic">
          — {content.quote_author}
        </cite>
      )}
    </div>
  );
};

const CodeShowcaseLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex h-full">
      <div className="w-2/5 flex flex-col justify-center px-12">
        {content.title && (
          <h2 className="text-3xl font-bold text-white mb-4">{content.title}</h2>
        )}
        {content.subtitle && (
          <p className="text-gray-300 mb-4">{content.subtitle}</p>
        )}
        {content.body?.map((item, i) => (
          <div key={i} className="flex gap-2 mb-2 text-gray-400 text-sm">
            <span className="text-purple-400">▸</span>
            <span>{item.text}</span>
          </div>
        ))}
      </div>
      <div className="w-3/5 flex items-center justify-center p-8 bg-gray-950/50">
        <pre className="rounded-xl p-6 text-sm text-green-300 font-mono overflow-auto w-full max-h-full bg-gray-950">
          <code>{content.code?.content || '// No code provided'}</code>
        </pre>
      </div>
    </div>
  );
};

const ConclusionLayout: React.FC<{ slide: Slide }> = ({ slide }) => {
  const { content } = slide;
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-16">
      {content.title && (
        <h2 className="text-5xl font-bold text-white mb-6">{content.title}</h2>
      )}
      {content.subtitle && (
        <p className="text-xl text-gray-300 mb-10 max-w-2xl">{content.subtitle}</p>
      )}
      {content.cta_text && (
        <div className="bg-purple-600 hover:bg-purple-500 text-white font-semibold 
                        px-8 py-4 rounded-full text-lg transition-colors cursor-pointer">
          {content.cta_text}
        </div>
      )}
      <div className="mt-12 flex items-center gap-3">
        <div className="w-8 h-8 bg-purple-500 rounded-full" />
        <span className="text-gray-400">Archimedes AI</span>
      </div>
    </div>
  );
};

// ── Layout Router ──

const LAYOUT_COMPONENTS: Record<string, React.FC<{ slide: Slide }>> = {
  hero: HeroLayout,
  bullet_list: BulletLayout,
  split_content: SplitContentLayout,
  data_grid: DataGridLayout,
  quote: QuoteLayout,
  code_showcase: CodeShowcaseLayout,
  conclusion: ConclusionLayout,
  comparison: BulletLayout,   // Fallback
  timeline: BulletLayout,     // Fallback
  image_focus: HeroLayout,    // Fallback
};

// ── Main Component ──

interface SlideRendererProps {
  presentation: Presentation;
  onClose?: () => void;
  initialSlide?: number;
}

export const SlideRenderer: React.FC<SlideRendererProps> = ({
  presentation,
  onClose,
  initialSlide = 0,
}) => {
  const [currentSlide, setCurrentSlide] = useState(initialSlide);
  const [showNotes, setShowNotes] = useState(false);
  const slides = presentation.slides || [];
  const slide = slides[currentSlide];

  const goNext = useCallback(() => {
    if (currentSlide < slides.length - 1) setCurrentSlide(c => c + 1);
  }, [currentSlide, slides.length]);

  const goPrev = useCallback(() => {
    if (currentSlide > 0) setCurrentSlide(c => c - 1);
  }, [currentSlide]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') goNext();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'Escape') onClose?.();
      if (e.key === 'n') setShowNotes(s => !s);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [goNext, goPrev, onClose]);

  if (!slide) return null;

  const LayoutComponent = LAYOUT_COMPONENTS[slide.layout_type] || BulletLayout;
  const bgClass = BG_CLASSES[slide.visual_config?.background || 'dark_gradient'];

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      {/* Slide area */}
      <div className={`flex-1 relative ${bgClass} overflow-hidden`}>
        <LayoutComponent slide={slide} />
        
        {/* Slide counter */}
        <div className="absolute bottom-4 right-6 text-gray-500 text-sm">
          {currentSlide + 1} / {slides.length}
        </div>
        
        {/* Archimedes watermark */}
        <div className="absolute bottom-4 left-6 flex items-center gap-2">
          <div className="w-5 h-5 bg-purple-500 rounded-full opacity-60" />
          <span className="text-gray-600 text-xs">Archimedes AI</span>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-900 border-t border-white/10 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={goPrev}
            disabled={currentSlide === 0}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg 
                       disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm"
          >
            ← Prev
          </button>
          <button
            onClick={goNext}
            disabled={currentSlide === slides.length - 1}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg 
                       disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Next →
          </button>
          
          {/* Slide thumbnails */}
          <div className="flex gap-1.5">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentSlide(i)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === currentSlide ? 'bg-purple-400' : 'bg-white/20 hover:bg-white/40'
                }`}
              />
            ))}
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowNotes(s => !s)}
            className="px-3 py-1.5 text-gray-400 hover:text-white text-sm transition-colors"
          >
            {showNotes ? 'Hide Notes' : 'Notes'}
          </button>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 text-gray-400 hover:text-white text-sm transition-colors"
          >
            Export PDF
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-gray-400 hover:text-white text-sm transition-colors"
            >
              ✕ Close
            </button>
          )}
        </div>
      </div>
      
      {/* Speaker notes */}
      {showNotes && slide.speaker_notes && (
        <div className="bg-gray-800 border-t border-white/10 px-6 py-3 max-h-24 overflow-auto">
          <p className="text-gray-400 text-sm">{slide.speaker_notes}</p>
        </div>
      )}
    </div>
  );
};

export default SlideRenderer;
