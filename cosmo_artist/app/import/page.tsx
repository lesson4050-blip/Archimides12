'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'

interface ImportSlide {
  type: string
  title: string
  content: string
  bullets: string[]
  stats: { value: string; label: string }[]
}

interface ImportData {
  topic: string
  slides: ImportSlide[]
  style: string
}

export default function ImportPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [data, setData] = useState<ImportData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    try {
      const raw = searchParams.get('data')
      if (!raw) {
        setError('No data provided')
        setStatus('error')
        return
      }

      // Validate URL param length (security: prevent huge payloads)
      if (raw.length > 50_000) {
        setError('Data too large')
        setStatus('error')
        return
      }

      const decoded = decodeURIComponent(raw)
      const parsed: ImportData = JSON.parse(decoded)

      // Validate structure
      if (!parsed.slides || !Array.isArray(parsed.slides)) {
        setError('Invalid slide data')
        setStatus('error')
        return
      }

      setData(parsed)
      setStatus('success')
    } catch (e) {
      setError('Failed to parse slide data')
      setStatus('error')
    }
  }, [searchParams])

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <p className="text-gray-400">Loading slides...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center flex-col gap-4">
        <p className="text-red-400">Import failed: {error}</p>
        <button
          onClick={() => router.push('/')}
          className="text-sm text-gray-400 hover:text-white"
        >
          ← Back to Presenton
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">{data?.topic}</h1>
            <p className="text-gray-400 text-sm mt-1">
              {data?.slides.length} slides · {data?.style} style · Imported from Deep Research
            </p>
          </div>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors"
          >
            Open Editor →
          </button>
        </div>

        {/* Slide previews */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data?.slides.map((slide, i) => (
            <div
              key={i}
              className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-gray-500 uppercase">{slide.type}</span>
                <span className="text-xs text-gray-600">·</span>
                <span className="text-xs text-gray-500">Slide {i + 1}</span>
              </div>
              <h3 className="font-semibold text-white mb-2">{slide.title}</h3>
              {slide.content && (
                <p className="text-gray-400 text-sm">{slide.content.slice(0, 100)}{slide.content.length > 100 ? '...' : ''}</p>
              )}
              {slide.bullets.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {slide.bullets.slice(0, 3).map((b, j) => (
                    <li key={j} className="text-xs text-gray-400">→ {b}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-8 flex gap-3">
          <button
            onClick={() => {
              // Copy slide data to clipboard for manual paste
              navigator.clipboard.writeText(JSON.stringify(data?.slides, null, 2))
              alert('Slide JSON copied to clipboard!')
            }}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-gray-300 transition-colors"
          >
            Copy JSON
          </button>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-lg text-sm text-blue-300 transition-colors"
          >
            🎨 Open in Editor
          </button>
        </div>
      </div>
    </div>
  )
}
