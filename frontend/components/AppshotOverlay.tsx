'use client'

import { useEffect } from 'react'
import { useAppshots } from '@/hooks/useAppshots'

interface Props {
  onCapture?: (shot: any) => void
}

export default function AppshotOverlay({ onCapture }: Props) {
  const {
    isSelecting,
    selection,
    showAnnotation,
    annotation,
    setAnnotation,
    capturedShot,
    startCapture,
    cancelCapture,
    submitAppshot,
  } = useAppshots()

  return (
    <>
      {/* Selection overlay */}
      {isSelecting && (
        <div
          className="fixed inset-0 z-[9998] cursor-crosshair"
          style={{ background: 'rgba(0,0,0,0.3)' }}
        >
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/80 text-white text-xs px-3 py-1.5 rounded-full">
            Drag to select region · ESC to cancel
          </div>

          {/* Selection rectangle */}
          {selection && selection.width > 0 && (
            <div
              className="absolute border-2 border-blue-400 bg-blue-400/10"
              style={{
                left: selection.x,
                top: selection.y,
                width: selection.width,
                height: selection.height,
              }}
            />
          )}
        </div>
      )}

      {/* Annotation popup */}
      {showAnnotation && capturedShot && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60">
          <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl p-4 w-full max-w-lg shadow-2xl">
            {/* Preview */}
            <div className="mb-3 rounded-lg overflow-hidden border border-[#333]">
              <img
                src={capturedShot.imageDataUrl}
                alt="Selected region"
                className="w-full object-contain max-h-48"
              />
            </div>

            {/* Annotation input */}
            <textarea
              autoFocus
              value={annotation}
              onChange={e => setAnnotation(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && e.ctrlKey) submitAppshot()
                if (e.key === 'Escape') cancelCapture()
              }}
              placeholder="Add a comment... (Ctrl+Enter to send)"
              className="w-full bg-[#262626] border border-[#444] rounded-xl p-3 text-sm text-white placeholder-gray-500 resize-none outline-none focus:border-[#666] mb-3"
              rows={3}
            />

            <div className="flex gap-2 justify-end">
              <button
                onClick={cancelCapture}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={submitAppshot}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-xl transition-colors"
              >
                Send to Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
