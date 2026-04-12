"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

interface VoiceVisualizerProps {
  isActive: boolean;
}

export default function VoiceVisualizer({ isActive }: VoiceVisualizerProps) {
  const [volumes, setVolumes] = useState<number[]>(new Array(25).fill(10));
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (isActive) {
      startVisualizer();
    } else {
      stopVisualizer();
    }

    return () => stopVisualizer();
  }, [isActive]);

  const startVisualizer = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const update = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        // Map frequency data to a smaller array for visualization
        const newVolumes = Array.from(dataArray)
          .slice(0, 25)
          .map(v => Math.max(10, v / 4)); // Ensure min height and scale
        
        setVolumes(newVolumes);
        animationFrameRef.current = requestAnimationFrame(update);
      };

      update();
    } catch (err) {
      console.error("Error accessing microphone for visualizer:", err);
    }
  };

  const stopVisualizer = () => {
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
    }
    if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
    }
    setVolumes(new Array(25).fill(10));
  };

  return (isActive ? (
    <div className="w-full h-16 flex items-center justify-center gap-1 px-4">
      {volumes.map((vol, i) => (
        <motion.div
          key={i}
          animate={{ height: vol }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="w-1.5 rounded-full bg-gradient-to-t from-blue-600 via-purple-500 to-blue-400 opacity-80 shadow-[0_0_10px_rgba(59,130,246,0.3)]"
        />
      ))}
    </div>
  ) : null);
}
