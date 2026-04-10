import os
from typing import Dict, Any
from gtts import gTTS
import groq
from backend.config import settings

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
        try:
            if action == "tts":
                if not text:
                    return {"success": False, "error": "text is required for tts"}
                path = path or "/home/ubuntu/workspace/output.mp3"
                
                # Использование gTTS для генерации (бесплатно)
                tts = gTTS(text=text, lang=lang)
                tts.save("temp_tts.mp3")
                
                # Перенос в песочницу
                from backend.sandbox.singleton import sandbox_manager
                with open("temp_tts.mp3", "rb") as f:
                    content = f.read()
                
                import base64
                b64 = base64.b64encode(content).decode()
                cmd = f"echo '{b64}' | base64 -d > {path}"
                await sandbox_manager.executor.run_command(
                    kwargs.get("session_id", ""), cmd
                )
                try:
                    os.remove("temp_tts.mp3")
                except Exception:
                    pass
                
                return {"success": True, "output": f"Audio saved to {path}", "path": path}
            
            elif action == "stt":
                if not path:
                    return {"success": False, "error": "path is required for stt"}
                
                client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
                
                # Вытащить файл из песочницы
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
                except Exception:
                    pass
                    
                return {"success": True, "output": transcription.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
