'use client'

import { useState } from 'react'

interface Slide {
  type: string
  title: string
  content: string
  bullets: string[]
  stats: { value: string; label: string }[]
}

interface ResearchResult {
  topic: string
  slide_count: number
  style: string
  elapsed_seconds: number
  slides: Slide[]
  search_used: boolean
  model: string
}

const STYLES = [
  { value: 'professional', label: '💼 Professional' },
  { value: 'minimal', label: '⬜ Minimal' },
  { value: 'creative', label: '🎨 Creative' },
  { value: 'technical', label: '⚙️ Technical' },
]

const TYPE_COLORS: Record<string, string> = {
  title:   'from-blue-600/20 to-purple-600/20 border-blue-500/30',
  closing: 'from-green-600/20 to-teal-600/20 border-green-500/30',
  stats:   'from-orange-600/20 to-yellow-600/20 border-orange-500/30',
  quote:   'from-pink-600/20 to-rose-600/20 border-pink-500/30',
  default: 'from-gray-700/30 to-gray-800/30 border-gray-600/30',
}

export default function DeepResearch() {
  const [topic, setTopic] = useState('')
  const [slideCount, setSlideCount] = useState(6)
  const [style, setStyle] = useState('professional')
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeSlide, setActiveSlide] = useState(0)

  const runResearch = async () => {
    if (!topic.trim() || loading) return
    if (topic.length > 500) {
      setError('Topic too long (max 500 characters)')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setActiveSlide(0)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
      const resp = await fetch(`${apiUrl}/api/v1/research-to-slides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          slide_count: slideCount,
          style,
        }),
        signal: AbortSignal.timeout(90000),
      })

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || `Error ${resp.status}`)
      }

      const data: ResearchResult = await resp.json()
      setResult(data)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.name === 'TimeoutError' ? 'Research timed out (90s)' : err.message)
      } else {
        setError('Unknown error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  const currentSlide = result?.slides[activeSlide]
  const colorClass = TYPE_COLORS[currentSlide?.type ?? ''] ?? TYPE_COLORS.default

  return (
    <div className="flex flex-col gap-4 p-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xl">🔬</span>
        <h2 className="text-lg font-semibold text-white">Deep Research → Slides</h2>
        <span className="text-xs text-gray-500 ml-2">
          Research any topic and generate a presentation instantly
        </span>
      </div>

      {/* Controls */}
      <div className="flex flex-col gap-3">
        <textarea
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) runResearch() }}
          placeholder="Enter research topic (e.g. 'The future of quantum computing')"
          maxLength={500}
          rows={2}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-gray-500"
        />

        <div className="flex items-center gap-3 flex-wrap">
          {/* Style selector */}
          <div className="flex gap-1">
            {STYLES.map(s => (
              <button
                key={s.value}
                onClick={() => setStyle(s.value)}
                className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                  style === s.value
                    ? 'bg-white/20 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Slide count */}
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-gray-500">Slides:</span>
            {[4, 6, 8, 10].map(n => (
              <button
                key={n}
                onClick={() => setSlideCount(n)}
                className={`text-xs w-8 h-7 rounded transition-colors ${
                  slideCount === n
                    ? 'bg-white/20 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {n}
              </button>
            ))}
          </div>

          <button
            onClick={runResearch}
            disabled={loading || !topic.trim()}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
          >
            {loading ? '⟳ Researching...' : '🔬 Research & Generate'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
          <div className="text-3xl mb-3 animate-pulse">🔬</div>
          <p className="text-gray-300 text-sm">Researching and generating slides...</p>
          <p className="text-gray-500 text-xs mt-1">This may take 20-40 seconds</p>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="flex flex-col gap-4">
          {/* Meta bar */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>📊 {result.slide_count} slides</span>
            <span>⏱️ {result.elapsed_seconds}s</span>
            <span>{result.search_used ? '🌐 Web researched' : '🧠 From knowledge'}</span>
            <span className="truncate">🤖 {result.model}</span>
          </div>

          {/* Slide navigation */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {result.slides.map((slide, i) => (
              <button
                key={i}
                onClick={() => setActiveSlide(i)}
                className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-lg transition-colors ${
                  i === activeSlide
                    ? 'bg-white/20 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {i + 1}. {slide.title.slice(0, 20)}{slide.title.length > 20 ? '...' : ''}
              </button>
            ))}
          </div>

          {/* Active slide */}
          {currentSlide && (
            <div className={`rounded-xl border bg-gradient-to-br p-6 min-h-[300px] flex flex-col gap-4 ${colorClass}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400 uppercase tracking-wider">
                  {currentSlide.type} · Slide {activeSlide + 1}/{result.slide_count}
                </span>
                <button
                  onClick={() => navigator.clipboard.writeText(
                    JSON.stringify(currentSlide, null, 2)
                  )}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  Copy JSON
                </button>
              </div>

              <h3 className="text-2xl font-bold text-white">{currentSlide.title}</h3>

              {currentSlide.content && (
                <p className="text-gray-300 text-sm leading-relaxed">{currentSlide.content}</p>
              )}

              {currentSlide.bullets.length > 0 && (
                <ul className="space-y-2">
                  {currentSlide.bullets.map((b, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                      <span className="text-blue-400 mt-0.5">→</span>
                      {b}
                    </li>
                  ))}
                </ul>
              )}

              {currentSlide.stats.length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  {currentSlide.stats.map((s, i) => (
                    <div key={i} className="bg-white/10 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-white">{s.value}</div>
                      <div className="text-xs text-gray-400 mt-1">{s.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Navigation arrows */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setActiveSlide(Math.max(0, activeSlide - 1))}
              disabled={activeSlide === 0}
              className="text-sm px-4 py-2 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-gray-300 rounded-lg transition-colors"
            >
              ← Previous
            </button>
            <span className="text-xs text-gray-500">
              {activeSlide + 1} / {result.slide_count}
            </span>
            <button
              onClick={() => setActiveSlide(Math.min(result.slide_count - 1, activeSlide + 1))}
              disabled={activeSlide === result.slide_count - 1}
              className="text-sm px-4 py-2 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-gray-300 rounded-lg transition-colors"
            >
              Next →
            </button>
          </div>

          {/* Export hint */}
          <div className="text-xs text-gray-600 text-center">
            Open cosmo_artist to convert these slides to a full presentation
          </div>
        </div>
      )}
    </div>
  )
}
