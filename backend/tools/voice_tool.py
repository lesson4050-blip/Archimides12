import os
from typing import Dict, Any


class VoiceTool:
    """Генерация речи и распознавание аудио через Groq Whisper/gTTS."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "voice",
                "description": "Convert text-to-speech or speech-to-text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["tts", "stt"]},
                        "text": {"type": "string", "description": "For TTS"},
                        "path": {"type": "string", "description": "File path for STT/TTS output"},
                        "lang": {"type": "string", "default": "en"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, text: str = None, 
                      path: str = None, lang: str = "en", **kwargs) -> Dict[str, Any]:
        if action in ("tts", "speak"):
            return await self._speak_gtts(text, lang, path, **kwargs)
        elif action in ("stt", "transcribe"):
            return await self._transcribe(path, **kwargs)
        return {"success": False, "error": f"Unknown action: {action}"}

    async def _speak_gtts(self, text: str, language: str = "en", 
                          path: str = None, **kwargs) -> Dict[str, Any]:
        try:
            from gtts import gTTS  # lazy import
        except ImportError:
            return {"success": False, "error": "gTTS not installed. Run: pip install gtts"}
        
        try:
            if not text:
                return {"success": False, "error": "text is required for tts"}
            
            # OS-agnostic default path
            if not path:
                import tempfile
                path = os.path.join(
                    tempfile.gettempdir(), "archimedes_tts_output.mp3"
                )
            
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Write directly to target path (avoid shell base64 piping)
            tts.save(path)
            
            return {
                "success": True,
                "output": f"Audio saved to {path}",
                "path": path,
                "engine": "gTTS"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _transcribe(self, path: str = None, **kwargs) -> Dict[str, Any]:
        try:
            from groq import AsyncGroq  # lazy import
        except ImportError:
            return {"success": False, "error": "groq not installed. Run: pip install groq"}
        
        try:
            if not path:
                return {"success": False, "error": "path is required for stt"}
            
            from backend.config import settings
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            
            from backend.sandbox.singleton import sandbox_manager
            result = await sandbox_manager.executor.run_command(
                kwargs.get("session_id", ""), 
                f"base64 {path}"
            )
            if not result.get("success"):
                return {"success": False, "error": f"Failed to read {path}"}
            
            import base64
            audio_data = base64.b64decode(result["output"].strip())
            
            with open("temp_stt.mp3", "wb") as f:
                f.write(audio_data)
            
            with open("temp_stt.mp3", "rb") as file:
                transcription = await client.audio.transcriptions.create(
                    file=(path.split("/")[-1], file.read()),
                    model="whisper-large-v3",
                )
            
            try:
                os.remove("temp_stt.mp3")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
                
            return {"success": True, "output": transcription.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
