import os
import logging
import asyncio
import subprocess
import shlex
from typing import Dict, Any, List, Optional
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

logger = logging.getLogger(__name__)

class VideoTool:
    """
    Инструмент для обработки видео с использованием ffmpeg.
    Обеспечивает конвертацию, обрезку и извлечение аудио.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "video",
            "description": "Обработка видео с использованием ffmpeg: конвертация, обрезка, извлечение аудио.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["convert", "trim", "extract_audio", "info"]},
                    "input_path": {"type": "string", "description": "Путь к исходному видео"},
                    "output_path": {"type": "string", "description": "Путь к выходному файлу"},
                    "start_time": {"type": "string", "description": "Время начала (00:00:00)"},
                    "duration": {"type": "string", "description": "Продолжительность (00:00:10)"}
                },
                "required": ["action", "input_path"]
            }
        }

    async def execute(self, action: str, input_path: str, **kwargs) -> Dict[str, Any]:
        try:
            if not os.path.exists(input_path):
                return {"success": False, "error": f"Файл не найден: {input_path}"}
            
            output_path = kwargs.get("output_path", "output_video.mp4")
            
            if action == "convert":
                safe_input = shlex.quote(input_path)
                safe_output = shlex.quote(output_path)
                cmd = f"ffmpeg -i {safe_input} {safe_output} -y"
            elif action == "trim":
                import re
                time_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}(\.\d+)?$')
                start = kwargs.get("start_time", "00:00:00")
                duration = kwargs.get("duration", "00:00:10")
                
                if not time_pattern.match(start):
                    return {"success": False, "error": "Invalid start_time format. Use HH:MM:SS"}
                if not time_pattern.match(duration):
                    return {"success": False, "error": "Invalid duration format. Use HH:MM:SS"}
                
                safe_input = shlex.quote(input_path)
                safe_output = shlex.quote(output_path)
                cmd = f"ffmpeg -i {safe_input} -ss {start} -t {duration} -c copy {safe_output} -y"
            elif action == "extract_audio":
                output_path = kwargs.get("output_path", "audio.mp3")
                safe_input = shlex.quote(input_path)
                safe_output = shlex.quote(output_path)
                cmd = f"ffmpeg -i {safe_input} -q:a 0 -map a {safe_output} -y"
            elif action == "info":
                safe_input = shlex.quote(input_path)
                cmd = f"ffprobe -v error -show_format -show_streams {safe_input}"
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
            
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {"success": True, "output": stdout.decode(), "file": output_path}
            else:
                return {"success": False, "error": stderr.decode()}
                
        except Exception as e:
            logger.error(f"Ошибка VideoTool: {e}")
            return {"success": False, "error": str(e)}

class AudioTool:
    """
    Инструмент для работы с аудио и TTS (Text-to-Speech).
    Использует бесплатные библиотеки gTTS для генерации речи.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "audio",
            "description": "Работа со звуком и генерация речи (TTS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["tts", "info"]},
                    "text": {"type": "string", "description": "Текст для озвучки"},
                    "lang": {"type": "string", "description": "Язык (ru, en)", "default": "ru"},
                    "output_path": {"type": "string", "description": "Путь к аудиофайлу"}
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        try:
            if action == "tts":
                from gtts import gTTS
                text = kwargs.get("text")
                lang = kwargs.get("lang", "ru")
                output_path = kwargs.get("output_path", "speech.mp3")
                
                tts = gTTS(text=text, lang=lang)
                tts.save(output_path)
                return {"success": True, "path": output_path}
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
        except Exception as e:
            logger.error(f"Ошибка AudioTool: {e}")
            return {"success": False, "error": str(e)}

class SheetsTool:
    """
    Инструмент для работы с Google Sheets.
    Обеспечивает чтение и запись данных в таблицы.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "sheets",
            "description": "Работа с Google Sheets: чтение и запись данных.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write", "append"]},
                    "spreadsheet_id": {"type": "string", "description": "ID таблицы или название"},
                    "range": {"type": "string", "description": "Диапазон (Sheet1!A1:B10)"},
                    "values": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
                },
                "required": ["action", "spreadsheet_id"]
            }
        }

    async def execute(self, action: str, spreadsheet_id: str, **kwargs) -> Dict[str, Any]:
        if not SHEETS_AVAILABLE:
            return {"success": False, "error": "Библиотека gspread не установлена. Установите её с помощью 'pip install gspread oauth2client'"}
            
        try:
            # Требует credentials.json для работы
            creds_path = os.environ.get("GOOGLE_SHEETS_CREDS", "credentials.json")
            if not os.path.exists(creds_path):
                return {"success": False, "error": "Файл учетных данных Google Sheets (credentials.json) не найден."}
            
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(spreadsheet_id).sheet1
            
            if action == "read":
                data = sheet.get_all_values()
                return {"success": True, "data": data}
            elif action == "write":
                values = kwargs.get("values", [])
                sheet.update('A1', values)
                return {"success": True}
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
        except Exception as e:
            logger.error(f"Ошибка SheetsTool: {e}")
            return {"success": False, "error": str(e)}

