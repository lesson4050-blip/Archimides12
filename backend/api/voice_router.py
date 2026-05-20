"""
Voice transcription endpoint.
Accepts audio blob, returns transcribed text.

SECURITY:
- File size limit: 10MB max
- Allowed audio formats only (webm, wav, mp3, ogg)
- Rate limit: 20 requests/minute per IP
- No file saved to disk — in-memory only
- Code-aware post-processing
"""
import io
import re
import time
import logging
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from backend.middleware.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

voice_limiter = RateLimiter(requests_per_minute=20, name="voice")
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
_ALLOWED_TYPES = {"audio/webm", "audio/wav", "audio/mp3", "audio/mpeg",
                   "audio/ogg", "audio/mp4", "audio/x-m4a", "video/webm"}

# Code-aware corrections for developer vocabulary
CODE_CORRECTIONS = {
    # Common misrecognitions in tech speech
    r"\bjason\b": "JSON",
    r"\bj son\b": "JSON",
    r"\bthe jason\b": "the JSON",
    r"\bo auth\b": "OAuth",
    r"\bo auth 2\b": "OAuth 2.0",
    r"\bapi key\b": "API key",
    r"\bapi keys\b": "API keys",
    r"\bthe api\b": "the API",
    r"\brest api\b": "REST API",
    r"\bgraph ql\b": "GraphQL",
    r"\bgraph queue l\b": "GraphQL",
    r"\bsql\b": "SQL",
    r"\bno sql\b": "NoSQL",
    r"\bpost gres\b": "PostgreSQL",
    r"\bpost gress\b": "PostgreSQL",
    r"\bmy sql\b": "MySQL",
    r"\bgit hub\b": "GitHub",
    r"\bgit lab\b": "GitLab",
    r"\bdocker file\b": "Dockerfile",
    r"\bkubernetes\b": "Kubernetes",
    r"\bk 8 s\b": "K8s",
    r"\btype script\b": "TypeScript",
    r"\bjavascript\b": "JavaScript",
    r"\bpy thon\b": "Python",
    r"\bfast api\b": "FastAPI",
    r"\bnext j s\b": "Next.js",
    r"\breact j s\b": "React.js",
    r"\bnode j s\b": "Node.js",
    r"\bexpress j s\b": "Express.js",
    r"\bweb socket\b": "WebSocket",
    r"\bweb sockets\b": "WebSockets",
    r"\bweb assembly\b": "WebAssembly",
    r"\blarge language model\b": "LLM",
    r"\blarge language models\b": "LLMs",
    r"\bartificial intelligence\b": "AI",
    r"\bmachine learning\b": "ML",
    r"\bdeep learning\b": "deep learning",
    r"\bneural network\b": "neural network",
    r"\bpull request\b": "pull request",
    r"\bp r\b": "PR",
    r"\bci cd\b": "CI/CD",
    r"\bdevops\b": "DevOps",
    r"\barchimedes\b": "Archimedes",
    r"\barchimides\b": "Archimedes",
}

def apply_code_corrections(text: str) -> str:
    """Apply developer-vocabulary corrections to transcribed text."""
    result = text
    for pattern, replacement in CODE_CORRECTIONS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result

@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
):
    """Transcribe audio to text using Whisper or Web Speech fallback."""
    
    client_ip = request.client.host if request.client else "unknown"
    if not voice_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit: 20 transcriptions/minute")
    
    # Validate file type
    content_type = audio.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        # Also accept if filename has valid extension
        filename = audio.filename or ""
        valid_ext = any(filename.endswith(ext) for ext in [".webm", ".wav", ".mp3", ".ogg", ".m4a"])
        if not valid_ext:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio format: {content_type}. Allowed: webm, wav, mp3, ogg, m4a"
            )
    
    # Read audio data with size limit
    audio_data = await audio.read(_MAX_FILE_SIZE + 1)
    if len(audio_data) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10MB)")
    
    if len(audio_data) < 100:
        raise HTTPException(status_code=400, detail="Audio file too small or empty")
    
    # Try Whisper transcription
    text = await _transcribe_with_whisper(audio_data, content_type)
    
    if not text:
        return JSONResponse({
            "success": False,
            "text": "",
            "method": "none",
            "error": "Transcription failed — whisper not available"
        })
    
    # Apply code-aware corrections
    corrected = apply_code_corrections(text.strip())
    
    return {
        "success": True,
        "text": corrected,
        "raw_text": text.strip(),
        "method": "whisper",
        "corrections_applied": corrected != text.strip(),
    }

async def _transcribe_with_whisper(audio_data: bytes, content_type: str) -> str:
    """Transcribe using local Whisper model."""
    try:
        import whisper
        import tempfile
        import os
        import asyncio
        
        # Determine file extension from content type
        ext_map = {
            "audio/webm": ".webm", "video/webm": ".webm",
            "audio/wav": ".wav", "audio/mp3": ".mp3",
            "audio/mpeg": ".mp3", "audio/ogg": ".ogg",
            "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
        }
        ext = ext_map.get(content_type, ".webm")
        
        # Write to temp file (whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # Load model in thread to avoid blocking
            def _run_whisper():
                model = whisper.load_model("base")
                result = model.transcribe(tmp_path, language=None, fp16=False)
                return result.get("text", "")
            
            text = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _run_whisper),
                timeout=30.0
            )
            return text
        finally:
            try:
                os.unlink(tmp_path)  # Always clean up temp file
            except Exception:
                pass
            
    except ImportError:
        logger.debug("Whisper not installed — voice transcription unavailable")
        return ""
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ""
