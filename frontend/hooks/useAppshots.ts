'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useAppStore } from '@/lib/store'

interface Region {
  x: number
  y: number
  width: number
  height: number
}

interface AppshotResult {
  imageDataUrl: string
  region: Region
  annotation: string
  timestamp: number
}

export function useAppshots() {
  const [isSelecting, setIsSelecting] = useState(false)
  const [selection, setSelection] = useState<Region | null>(null)
  const [showAnnotation, setShowAnnotation] = useState(false)
  const [annotation, setAnnotation] = useState('')
  const [capturedShot, setCapturedShot] = useState<AppshotResult | null>(null)
  const startRef = useRef<{ x: number; y: number } | null>(null)
  const overlayRef = useRef<HTMLDivElement | null>(null)
  const { setInput, appendAttachment } = useAppStore()

  // Start region selection mode
  const startCapture = useCallback(() => {
    setIsSelecting(true)
    setSelection(null)
    setAnnotation('')
    setShowAnnotation(false)
    document.body.style.cursor = 'crosshair'
  }, [])

  // Cancel selection
  const cancelCapture = useCallback(() => {
    setIsSelecting(false)
    setSelection(null)
    setShowAnnotation(false)
    document.body.style.cursor = ''
  }, [])

  // Mouse handlers for region drawing
  const handleMouseDown = useCallback((e: MouseEvent) => {
    if (!isSelecting) return
    startRef.current = { x: e.clientX, y: e.clientY }
  }, [isSelecting])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isSelecting || !startRef.current) return
    const start = startRef.current
    setSelection({
      x: Math.min(start.x, e.clientX),
      y: Math.min(start.y, e.clientY),
      width: Math.abs(e.clientX - start.x),
      height: Math.abs(e.clientY - start.y),
    })
  }, [isSelecting])

  const handleMouseUp = useCallback(async (e: MouseEvent) => {
    if (!isSelecting || !startRef.current) return
    
    const start = startRef.current
    const region: Region = {
      x: Math.min(start.x, e.clientX),
      y: Math.min(start.y, e.clientY),
      width: Math.abs(e.clientX - start.x),
      height: Math.abs(e.clientY - start.y),
    }

    // Minimum selection size
    if (region.width < 10 || region.height < 10) {
      cancelCapture()
      return
    }

    // Capture the selected region using html2canvas
    try {
      const html2canvas = (await import('html2canvas')).default
      const canvas = await html2canvas(document.body, {
        x: region.x + window.scrollX,
        y: region.y + window.scrollY,
        width: region.width,
        height: region.height,
        useCORS: true,
        logging: false,
      })
      
      const imageDataUrl = canvas.toDataURL('image/png')
      setCapturedShot({
        imageDataUrl,
        region,
        annotation: '',
        timestamp: Date.now(),
      })
      setSelection(region)
      setShowAnnotation(true)
      document.body.style.cursor = ''
    } catch (err) {
      console.error('Screenshot capture failed:', err)
      cancelCapture()
    }

    setIsSelecting(false)
    startRef.current = null
  }, [isSelecting, cancelCapture])

  // Attach event listeners
  useEffect(() => {
    if (isSelecting) {
      window.addEventListener('mousedown', handleMouseDown)
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      // ESC to cancel
      const handleKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') cancelCapture()
      }
      window.addEventListener('keydown', handleKey)
      return () => {
        window.removeEventListener('mousedown', handleMouseDown)
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseup', handleMouseUp)
        window.removeEventListener('keydown', handleKey)
      }
    }
  }, [isSelecting, handleMouseDown, handleMouseMove, handleMouseUp, cancelCapture])

  // Submit annotation + screenshot to chat
  const submitAppshot = useCallback(() => {
    if (!capturedShot) return
    
    const finalShot: AppshotResult = {
      ...capturedShot,
      annotation: annotation.trim(),
    }
    
    // Append image as attachment
    if (typeof appendAttachment === 'function') {
      appendAttachment({
        type: 'appshot',
        imageDataUrl: finalShot.imageDataUrl,
        annotation: finalShot.annotation,
        region: finalShot.region,
      })
    }
    
    // Prepend annotation to input
    if (annotation.trim()) {
      setInput(annotation.trim())
    }
    
    setCapturedShot(null)
    setShowAnnotation(false)
    setAnnotation('')
  }, [capturedShot, annotation, setInput, appendAttachment])

  return {
    isSelecting,
    selection,
    showAnnotation,
    annotation,
    setAnnotation,
    capturedShot,
    startCapture,
    cancelCapture,
    submitAppshot,
  }
}
