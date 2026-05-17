"""
Model Council UI — shows multiple model responses side by side.
Inspired by Perplexity Model Council.
Design: dark cards, color-coded by model label, expandable.
"""

'use client'

import { useState } from 'react'

interface CouncilResponse {
  label: string
  model: string
  text: string
  success: boolean
  error: string | null
  tokens?: number
}

interface CouncilResult {
  type: string
  task: string
  responses: CouncilResponse[]
  successful_count: number
  total_count: number
  elapsed_seconds: number
}

const LABEL_COLORS: Record<string, string> = {
  Creative: 'border-purple-500 bg-purple-500/10',
  Precise:  'border-blue-500 bg-blue-500/10',
  Balanced: 'border-green-500 bg-green-500/10',
}

const LABEL_BADGE: Record<string, string> = {
  Creative: 'bg-purple-500/20 text-purple-300',
  Precise:  'bg-blue-500/20 text-blue-300',
  Balanced: 'bg-green-500/20 text-green-300',
}

export default function ModelCouncil() {
  const [task, setTask] = useState('')
  const [result, setResult] = useState<CouncilResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const runCouncil = async () => {
    if (!task.trim() || loading) return
    
    // Client-side input validation
    if (task.length > 2000) {
      setError('Task too long (max 2000 characters)')
      return
    }
    
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
      const resp = await fetch(`${apiUrl}/api/v1/council`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task.trim(), mode: 'council' }),
        // Abort if takes too long
        signal: AbortSignal.timeout(50000),
      })

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || `Error ${resp.status}`)
      }

      const data: CouncilResult = await resp.json()
      setResult(data)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.name === 'TimeoutError' ? 'Request timed out' : err.message)
      } else {
        setError('Unknown error')
      }
    } finally {
      setLoading(false)
    }
  }

  const toggleExpand = (label: string) => {
    setExpanded(prev => ({ ...prev, [label]: !prev[label] }))
  }

  return (
    <div className="flex flex-col gap-4 p-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xl">⚖️</span>
        <h2 className="text-lg font-semibold text-white">Model Council</h2>
        <span className="text-xs text-gray-500 ml-2">
          Run your task across multiple model configs simultaneously
        </span>
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={task}
          onChange={e => setTask(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && e.ctrlKey) runCouncil()
          }}
          placeholder="Ask anything... (Ctrl+Enter to run)"
          maxLength={2000}
          rows={3}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-gray-500"
        />
        <button
          onClick={runCouncil}
          disabled={loading || !task.trim()}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors self-start"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⟳</span> Running...
            </span>
          ) : 'Run Council'}
        </button>
      </div>

      {/* Character count */}
      <div className="text-xs text-gray-600 text-right -mt-2">
        {task.length}/2000
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['Creative', 'Precise', 'Balanced'].map(label => (
            <div
              key={label}
              className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 animate-pulse h-48"
            >
              <div className="h-4 bg-gray-700 rounded w-1/3 mb-3" />
              <div className="space-y-2">
                <div className="h-3 bg-gray-700 rounded" />
                <div className="h-3 bg-gray-700 rounded w-4/5" />
                <div className="h-3 bg-gray-700 rounded w-3/5" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Meta */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>✅ {result.successful_count}/{result.total_count} succeeded</span>
            <span>⏱️ {result.elapsed_seconds}s</span>
          </div>

          {/* Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {result.responses.map(resp => {
              const isExpanded = expanded[resp.label]
              const colorClass = LABEL_COLORS[resp.label] || 'border-gray-600 bg-gray-800/50'
              const badgeClass = LABEL_BADGE[resp.label] || 'bg-gray-700 text-gray-300'
              const preview = resp.text.slice(0, 300)
              const hasMore = resp.text.length > 300

              return (
                <div
                  key={resp.label}
                  className={`rounded-xl border p-4 flex flex-col gap-3 transition-all ${colorClass}`}
                >
                  {/* Card header */}
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${badgeClass}`}>
                      {resp.label}
                    </span>
                    <span className="text-xs text-gray-500 truncate max-w-[120px]">
                      {resp.model}
                    </span>
                  </div>

                  {/* Content */}
                  {resp.success ? (
                    <div className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                      {isExpanded ? resp.text : preview}
                      {hasMore && !isExpanded && (
                        <span className="text-gray-500">...</span>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-red-400">
                      ❌ {resp.error || 'Failed'}
                    </div>
                  )}

                  {/* Expand / Copy */}
                  {resp.success && (
                    <div className="flex items-center gap-2 mt-auto pt-2 border-t border-white/5">
                      {hasMore && (
                        <button
                          onClick={() => toggleExpand(resp.label)}
                          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                        >
                          {isExpanded ? 'Show less' : 'Show more'}
                        </button>
                      )}
                      <button
                        onClick={() => navigator.clipboard.writeText(resp.text)}
                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors ml-auto"
                      >
                        Copy
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
