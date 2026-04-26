"""
Audio Synthesis Tool — generates real WAV audio files from mathematical
waveforms. Pure Python, zero external dependencies (stdlib only).

This is a genuine new capability: the agent cannot produce binary audio
through shell/file tools. Every other "domain tool" can be replicated
by having the LLM write a script — this one cannot.
"""
import io
import wave
import math
import struct
import logging
import tempfile
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ── Note / frequency mapping (A4 = 440 Hz, 12-TET) ──────────────────

_NOTE_SEMITONES = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def _note_to_freq(note: str) -> float:
    """Convert note name (e.g. 'A4', 'C#5', 'Bb3') to Hz. 'R' = rest."""
    note = note.strip()
    if not note or note.upper() == "R":
        return 0.0
    # Parse: note name may be 1 or 2 chars, rest is octave
    if len(note) >= 3 and note[1] in ("#", "b"):
        name, octave = note[:2], int(note[2:])
    elif len(note) >= 2:
        name, octave = note[0].upper(), int(note[1:])
    else:
        raise ValueError(f"Cannot parse note: {note!r}")
    semitone = _NOTE_SEMITONES.get(name)
    if semitone is None:
        raise ValueError(f"Unknown note name: {name!r}")
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


# ── Waveform generators ─────────────────────────────────────────────

def _waveform(freq: float, t: float, kind: str) -> float:
    if freq <= 0:
        return 0.0
    phase = freq * t
    if kind == "sine":
        return math.sin(2 * math.pi * phase)
    elif kind == "square":
        return 1.0 if (phase % 1.0) < 0.5 else -1.0
    elif kind == "sawtooth":
        return 2.0 * (phase % 1.0) - 1.0
    elif kind == "triangle":
        return 2.0 * abs(2.0 * (phase % 1.0) - 1.0) - 1.0
    return math.sin(2 * math.pi * phase)


# ── ADSR envelope ────────────────────────────────────────────────────

def _adsr(i: int, total: int, sr: int,
          a=0.01, d=0.05, s_level=0.7, r=0.05) -> float:
    """Compute ADSR envelope value for sample index i."""
    a_n = int(a * sr)
    d_n = int(d * sr)
    r_n = int(r * sr)
    r_start = total - r_n

    if i < a_n:
        return i / max(a_n, 1)
    elif i < a_n + d_n:
        progress = (i - a_n) / max(d_n, 1)
        return 1.0 - progress * (1.0 - s_level)
    elif i < r_start:
        return s_level
    else:
        progress = (i - r_start) / max(r_n, 1)
        return s_level * max(1.0 - progress, 0.0)


# ── WAV writer (stdlib wave module — no manual headers) ──────────────

def _to_wav(samples: List[float], sr: int = 44100) -> bytes:
    """Convert float samples to 16-bit mono WAV bytes."""
    if not samples:
        raise ValueError("Empty sample buffer")
    peak = max(abs(s) for s in samples) or 1.0
    scale = 32767.0 / peak * 0.92  # 8% headroom against clipping
    packed = struct.pack(
        f"<{len(samples)}h",
        *(max(-32768, min(32767, int(s * scale))) for s in samples),
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(packed)
    return buf.getvalue()


# ── DTMF frequency pairs ────────────────────────────────────────────

_DTMF = {
    "1": (697, 1209), "2": (697, 1336), "3": (697, 1477), "A": (697, 1633),
    "4": (770, 1209), "5": (770, 1336), "6": (770, 1477), "B": (770, 1633),
    "7": (852, 1209), "8": (852, 1336), "9": (852, 1477), "C": (852, 1633),
    "*": (941, 1209), "0": (941, 1336), "#": (941, 1477), "D": (941, 1633),
}


class AudioSynthTool:
    """
    Synthesize audio files (WAV) from code.
    Pure stdlib Python — no APIs, no pip dependencies.
    """

    SAMPLE_RATE = 44100

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "audio_synth",
                "description": (
                    "Synthesize audio files (WAV) from code. No API needed. "
                    "Actions: tone (sine/square/sawtooth/triangle), "
                    "melody (note sequence with ADSR), chord (polyphonic), "
                    "dtmf (phone dial tones), note_freq (reference table)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["tone", "melody", "chord", "dtmf", "note_freq"],
                        },
                        "frequency": {
                            "type": "number",
                            "description": "Hz (tone action, default 440)",
                        },
                        "duration": {
                            "type": "number",
                            "description": "Seconds (default 1.0)",
                        },
                        "waveform": {
                            "type": "string",
                            "enum": ["sine", "square", "sawtooth", "triangle"],
                        },
                        "notes": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": 'List of {note:"C4", duration:0.5}',
                        },
                        "digits": {
                            "type": "string",
                            "description": "DTMF digits (0-9, *, #, A-D)",
                        },
                        "output_path": {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(
        self,
        action: str,
        frequency: float = 440.0,
        duration: float = 1.0,
        waveform: str = "sine",
        notes: Optional[List[dict]] = None,
        digits: str = "",
        output_path: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        SR = self.SAMPLE_RATE
        try:
            if action == "tone":
                return self._tone(frequency, duration, waveform, output_path, SR)
            elif action == "melody":
                return self._melody(notes, waveform, output_path, SR)
            elif action == "chord":
                return self._chord(notes, duration, waveform, output_path, SR)
            elif action == "dtmf":
                return self._dtmf(digits, output_path, SR)
            elif action == "note_freq":
                return self._note_freq_table()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"AudioSynthTool.{action} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── action implementations ───────────────────────────────────────

    def _tone(self, freq, dur, wf, path, sr) -> Dict[str, Any]:
        if not (1 <= freq <= 22000):
            return {"success": False, "error": "Frequency must be 1–22 000 Hz"}
        dur = max(0.01, min(dur, 30.0))
        n = int(sr * dur)
        samples = [
            _waveform(freq, i / sr, wf) * _adsr(i, n, sr, a=0.005, r=0.02)
            for i in range(n)
        ]
        return self._save(samples, sr, path, f"archimedes_{wf}_{int(freq)}Hz.wav",
                          f"{wf} tone: {freq} Hz, {dur:.2f}s")

    def _melody(self, notes, wf, path, sr) -> Dict[str, Any]:
        if not notes:
            notes = [{"note": n, "duration": 0.35}
                     for n in ("C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5")]
        samples: List[float] = []
        log: List[str] = []
        for nd in notes:
            name = str(nd.get("note", "A4"))
            dur = max(0.05, min(float(nd.get("duration", 0.4)), 10.0))
            n = int(sr * dur)
            if name.upper() == "R":
                samples.extend([0.0] * n)
                log.append("R")
                continue
            freq = _note_to_freq(name)
            log.append(name)
            for i in range(n):
                s = _waveform(freq, i / sr, wf)
                e = _adsr(i, n, sr, a=0.01, d=0.05, s_level=0.6, r=0.04)
                samples.append(s * e)
        if not samples:
            return {"success": False, "error": "Empty note sequence"}
        total_dur = len(samples) / sr
        return self._save(samples, sr, path, "archimedes_melody.wav",
                          f"Melody: {' '.join(log)} ({total_dur:.1f}s, {wf})")

    def _chord(self, notes, dur, wf, path, sr) -> Dict[str, Any]:
        if not notes:
            notes = [{"note": "C4"}, {"note": "E4"}, {"note": "G4"}]
        dur = max(0.1, min(float(dur), 10.0))
        n = int(sr * dur)
        freqs = []
        log = []
        for nd in notes:
            name = str(nd.get("note", "C4"))
            freqs.append(_note_to_freq(name))
            log.append(name)
        inv_count = 1.0 / max(len(freqs), 1)
        samples = []
        for i in range(n):
            t = i / sr
            mix = sum(_waveform(f, t, wf) for f in freqs) * inv_count
            e = _adsr(i, n, sr, a=0.02, d=0.08, s_level=0.6, r=0.08)
            samples.append(mix * e)
        return self._save(samples, sr, path, "archimedes_chord.wav",
                          f"Chord: {'+'.join(log)} ({dur:.1f}s, {wf})")

    def _dtmf(self, digits, path, sr) -> Dict[str, Any]:
        if not digits:
            return {"success": False, "error": "digits parameter required"}
        tone_dur = 0.08  # 80 ms per tone (ITU standard)
        gap_dur = 0.05   # 50 ms gap
        samples: List[float] = []
        valid = []
        for ch in str(digits).upper():
            pair = _DTMF.get(ch)
            if not pair:
                continue
            valid.append(ch)
            f1, f2 = pair
            n = int(sr * tone_dur)
            for i in range(n):
                t = i / sr
                s = 0.5 * math.sin(2 * math.pi * f1 * t) + \
                    0.5 * math.sin(2 * math.pi * f2 * t)
                fade = min(i, n - 1 - i, int(sr * 0.002)) / max(int(sr * 0.002), 1)
                samples.append(s * min(fade, 1.0))
            samples.extend([0.0] * int(sr * gap_dur))
        if not valid:
            return {"success": False, "error": "No valid DTMF digits found"}
        return self._save(samples, sr, path, "archimedes_dtmf.wav",
                          f"DTMF: {''.join(valid)}")

    def _note_freq_table(self) -> Dict[str, Any]:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        lines = ["=== Equal Temperament (A4 = 440 Hz) ===", ""]
        for octave in range(2, 8):
            row = []
            for n in names:
                f = _note_to_freq(f"{n}{octave}")
                row.append(f"{n}{octave}:{f:>8.2f}")
            lines.append("  ".join(row))
        return {"success": True, "output": "\n".join(lines)}

    # ── shared save helper ───────────────────────────────────────────

    def _save(self, samples, sr, path, default_name, desc) -> Dict[str, Any]:
        wav_bytes = _to_wav(samples, sr)
        if not path:
            path = os.path.join(tempfile.gettempdir(), default_name)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(wav_bytes)
        return {
            "success": True,
            "output": (
                f"{desc}\n"
                f"File: {path} ({len(wav_bytes):,} bytes, {sr}Hz 16-bit mono)\n"
                f"Play: aplay '{path}'"
            ),
            "file_path": path,
        }
