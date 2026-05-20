import { useState, useRef, useCallback, useEffect } from 'react'
import { useAppStore } from '@/lib/store'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// Supported MIME types in order of preference
const PREFERRED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

function getSupportedMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  return PREFERRED_MIME_TYPES.find(t => MediaRecorder.isTypeSupported(t)) || ''
}

export function useVoiceMode() {
  const { setInput, setIsListening, isListening } = useAppStore()
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [useWebSpeech, setUseWebSpeech] = useState(false)
  const recognitionRef = useRef<any>(null)

  // Initialize Web Speech API Recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        const reco = new SpeechRecognition()
        reco.lang = navigator.language || 'ru-RU'
        reco.continuous = true
        reco.interimResults = true

        reco.onresult = (event: any) => {
          let currentTranscript = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript
          }
          setInput(prev => prev ? prev + ' ' + currentTranscript.trim() : currentTranscript.trim())
        }

        reco.onerror = (event: any) => {
          console.error('Speech recognition error', event.error)
          setVoiceError(`Web Speech error: ${event.error}`)
          setIsListening(false)
        }

        reco.onend = () => {
          setIsListening(false)
        }

        recognitionRef.current = reco
      }
    }
  }, [setInput, setIsListening])

  const startRecording = useCallback(async () => {
    setVoiceError(null)
    audioChunksRef.current = []

    if (useWebSpeech) {
      if (!recognitionRef.current) {
        setVoiceError('Web Speech API not supported or not initialized in this browser')
        return
      }
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        console.error('Failed to start SpeechRecognition:', err)
        setVoiceError('Failed to start Web Speech API')
        setIsListening(false)
      }
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,  // Whisper prefers 16kHz
          echoCancellation: true,
          noiseSuppression: true,
        }
      })
      streamRef.current = stream

      const mimeType = getSupportedMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(t => t.stop())
        
        if (audioChunksRef.current.length === 0) return
        
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType || 'audio/webm'
        })

        // Try Whisper backend
        const whisperText = await transcribeWithWhisper(audioBlob, mimeType)
        
        if (whisperText) {
          setInput(prev => prev ? prev + ' ' + whisperText : whisperText)
        } else {
          // Fall back to Web Speech API
          setVoiceError('Whisper unavailable — falling back to Web Speech API')
          setUseWebSpeech(true)
        }
        
        setIsTranscribing(false)
      }

      mediaRecorderRef.current = recorder
      recorder.start(100)  // Collect chunks every 100ms
      setIsListening(true)
      
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setVoiceError('Microphone access denied')
        } else {
          setVoiceError(`Microphone error: ${err.message}`)
          setUseWebSpeech(true)
        }
      } else {
        setUseWebSpeech(true)
      }
      setIsListening(false)
    }
  }, [setInput, setIsListening, useWebSpeech])

  const stopRecording = useCallback(() => {
    if (useWebSpeech) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch (e) {
          console.warn(e)
        }
      }
      setIsListening(false)
      return
    }

    if (mediaRecorderRef.current?.state === 'recording') {
      setIsTranscribing(true)
      mediaRecorderRef.current.stop()
    }
    setIsListening(false)
  }, [setIsListening, useWebSpeech])

  const toggleMic = useCallback(() => {
    if (isListening) {
      stopRecording()
    } else {
      startRecording()
    }
  }, [isListening, startRecording, stopRecording])

  return { toggleMic, isTranscribing, voiceError }
}

async function transcribeWithWhisper(
  audioBlob: Blob,
  mimeType: string
): Promise<string> {
  try {
    const formData = new FormData()
    const ext = mimeType.includes('ogg') ? '.ogg' : '.webm'
    formData.append('audio', audioBlob, `recording${ext}`)

    const response = await fetch(`${API_URL}/api/v1/voice/transcribe`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(35000),
    })

    if (!response.ok) {
      console.warn(`Whisper API error: ${response.status}`)
      return ''
    }

    const data = await response.json()
    return data.success ? data.text : ''
    
  } catch (err) {
    console.warn('Whisper transcription failed:', err)
    return ''
  }
}
