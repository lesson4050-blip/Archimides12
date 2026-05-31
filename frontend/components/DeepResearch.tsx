'use client'

import { useState } from 'react'
import { Microscope } from 'lucide-react'

interface MarpResult {
  success: boolean
  topic: string
  slide_count: number
  style: string
  elapsed_seconds: number
  markdown: string
  html: string
  search_used: boolean
  model: string
}

const STYLES = [
  { value: 'professional', label: '💼 Professional' },
  { value: 'minimal', label: '⬜ Minimal' },
  { value: 'creative', label: '🎨 Creative' },
  { value: 'technical', label: '⚙️ Technical' },
]

export default function DeepResearch() {
  const [topic, setTopic] = useState('')
  const [slideCount, setSlideCount] = useState(6)
  const [style, setStyle] = useState('professional')
  const [result, setResult] = useState<MarpResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview')
  const [exportingPdf, setExportingPdf] = useState(false)

  const runResearch = async () => {
    if (!topic.trim() || loading) return
    if (topic.length > 500) {
      setError('Topic too long (max 500 characters)')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setActiveTab('preview')

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
      const resp = await fetch(`${apiUrl}/api/v1/research-to-marp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          slide_count: slideCount,
          style,
        }),
        signal: AbortSignal.timeout(120000), // 2 minutes timeout for deep research + CLI compile
      })

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || `Error ${resp.status}`)
      }

      const data: MarpResult = await resp.json()
      setResult(data)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.name === 'TimeoutError' ? 'Research timed out (120s)' : err.message)
      } else {
        setError('Unknown error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  const downloadHtml = () => {
    if (!result) return
    const blob = new Blob([result.html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${result.topic.slice(0, 30).replace(/[^a-zA-Z0-9а-яА-Я]+/g, '_')}.html`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportPdf = async () => {
    if (!result || exportingPdf) return
    setExportingPdf(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
      const resp = await fetch(`${apiUrl}/api/v1/export-marp-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown: result.markdown }),
      })
      if (!resp.ok) throw new Error('PDF export failed')
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${result.topic.slice(0, 30).replace(/[^a-zA-Z0-9а-яА-Я]+/g, '_')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
      alert('Failed to export vector PDF. Please ensure node / marp-cli dependencies are met on the server.')
    } finally {
      setExportingPdf(false)
    }
  }

  return (
    <div className="flex flex-col gap-5 p-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <Microscope className="w-7 h-7 text-gray-400 animate-pulse" />
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Archimedes Marp Slides</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Deep web research synthesized instantly into premium Markdown presentations
            </p>
          </div>
        </div>
      </div>

      {/* Inputs and Controls */}
      <div className="flex flex-col gap-4 bg-white/[0.02] border border-white/10 rounded-2xl p-5 shadow-xl">
        <textarea
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) runResearch() }}
          placeholder="Enter research topic (e.g. 'The mechanism of CRISPR gene editing or history of Byzantine architecture')"
          maxLength={500}
          rows={2}
          className="w-full bg-gray-900/50 border border-white/10 rounded-xl p-4 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-purple-500/50 transition-colors"
        />

        <div className="flex items-center justify-between gap-3 flex-wrap">
          {/* Style Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-medium">Style:</span>
            <div className="flex gap-1.5">
              {STYLES.map(s => (
                <button
                  key={s.value}
                  onClick={() => setStyle(s.value)}
                  className={`text-xs px-3.5 py-2 rounded-lg font-medium transition-all ${
                    style === s.value
                      ? 'bg-purple-600/30 border border-purple-500/50 text-white'
                      : 'bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Slide Count Selector */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500 font-medium">Slides:</span>
              {[4, 6, 8, 10, 12].map(n => (
                <button
                  key={n}
                  onClick={() => setSlideCount(n)}
                  className={`text-xs w-9 h-8 rounded-lg font-semibold transition-all ${
                    slideCount === n
                      ? 'bg-purple-600/30 border border-purple-500/50 text-white'
                      : 'bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>

            <button
              onClick={runResearch}
              disabled={loading || !topic.trim()}
              className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-purple-500/10 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Researching...
                </>
              ) : (
                <>
                  <Microscope className="w-4 h-4" />
                  Generate Slides
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error Frame */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400 font-medium flex items-center gap-2 animate-shake">
          <span>⚠️</span>
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-12 flex flex-col items-center justify-center text-center shadow-inner min-h-[350px]">
          <div className="text-5xl mb-4 animate-bounce">🤖</div>
          <h3 className="text-lg font-bold text-white mb-2">Researching & Formatting slides</h3>
          <p className="text-gray-400 text-sm max-w-sm">
            Archimedes is querying search providers, analyzing articles, and synthesizing Markdown slides...
          </p>
          <div className="mt-6 flex gap-2">
            <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce delay-100" />
            <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce delay-200" />
            <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce delay-300" />
          </div>
        </div>
      )}

      {/* Presentation Workspace */}
      {result && !loading && (
        <div className="flex flex-col gap-4 animate-fadeIn">
          {/* Metadata Ribbon */}
          <div className="flex items-center justify-between bg-white/[0.02] border border-white/5 rounded-xl px-4 py-3 text-xs text-gray-400 flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <span>📊 <strong>{result.slide_count}</strong> slides</span>
              <span>⏱️ <strong>{result.elapsed_seconds}s</strong> elapsed</span>
              <span>{result.search_used ? '🌐 Web Researched' : '🧠 Internal Knowledge'}</span>
              <span className="truncate">🤖 Model: <strong>{result.model}</strong></span>
            </div>
            
            {/* View Mode Toggle */}
            <div className="flex bg-white/5 p-0.5 rounded-lg border border-white/5">
              <button
                onClick={() => setActiveTab('preview')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  activeTab === 'preview' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-400 hover:text-white'
                }`}
              >
                👁️ Preview
              </button>
              <button
                onClick={() => setActiveTab('code')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  activeTab === 'code' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-400 hover:text-white'
                }`}
              >
                📝 Markdown
              </button>
            </div>
          </div>

          {/* Active Workspace Tabs */}
          {activeTab === 'preview' ? (
            <div className="flex flex-col gap-3">
              {/* Responsive Widescreen Iframe Container */}
              <div className="w-full aspect-video rounded-2xl overflow-hidden border border-white/10 bg-gray-950 shadow-2xl relative">
                <iframe
                  srcDoc={result.html}
                  className="w-full h-full border-none"
                  title="Archimedes Presentation Preview"
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
              <p className="text-[11px] text-gray-500 text-center font-medium">
                💡 Click inside the preview window above, then use <strong>Right/Left arrows</strong> or <strong>Spacebar</strong> to navigate.
              </p>
            </div>
          ) : (
            <div className="relative">
              <pre className="bg-gray-950/70 border border-white/10 rounded-2xl p-5 text-xs text-purple-300/90 font-mono overflow-auto max-h-[480px] leading-relaxed">
                <code>{result.markdown}</code>
              </pre>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(result.markdown)
                  alert('Marp Markdown copied to clipboard!')
                }}
                className="absolute top-4 right-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium text-xs px-3.5 py-1.5 rounded-lg transition-colors"
              >
                📋 Copy Code
              </button>
            </div>
          )}

          {/* Export Action Block */}
          <div className="grid grid-cols-2 gap-4 mt-2">
            <button
              onClick={downloadHtml}
              className="py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-semibold text-white transition-all flex items-center justify-center gap-2 hover:shadow-lg hover:shadow-white/5"
            >
              <span>💾</span>
              Download Interactive HTML (Offline Presenter)
            </button>
            
            <button
              onClick={exportPdf}
              disabled={exportingPdf}
              className="py-3.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-500/10"
            >
              {exportingPdf ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Compiling PDF...
                </>
              ) : (
                <>
                  <span>📄</span>
                  Export Premium PDF
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
