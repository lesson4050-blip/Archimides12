import os
import logging
import asyncio
import shlex
from typing import Dict, Any
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

logger = logging.getLogger(__name__)

class VideoTool:
    name = "video"
    description = "Video processing — frame extraction and basic analysis"
    
    async def execute(self, action: str, input_path: str = "", **kwargs) -> Dict[str, Any]:
        if not input_path:
            return {"success": False, "error": "input_path required"}
        
        try:
            import cv2
            if action == "info":
                cap = cv2.VideoCapture(input_path)
                if not cap.isOpened():
                    return {"success": False, "error": f"Cannot open: {input_path}"}
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return {"success": True, "output": f"{w}x{h} @ {fps:.1f}fps, {int(frames)} frames"}
            else:
                return {"success": False, "error": f"Unknown action: {action}. Use: info"}
        except ImportError:
            return {
                "success": False,
                "error": "opencv-python not installed. Run: pip install opencv-python",
                "action": action
            }

class AudioTool:
    name = "audio"
    description = "Audio processing — transcription and text-to-speech"
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        if action == "transcribe":
            file_path = kwargs.get("file_path", "")
            if not file_path:
                return {"success": False, "error": "file_path required for transcription"}
            # Try whisper if available
            try:
                import whisper
                model = whisper.load_model("base")
                result = model.transcribe(file_path)
                return {"success": True, "output": result["text"]}
            except ImportError:
                return {
                    "success": False,
                    "error": "whisper not installed. Run: pip install openai-whisper",
                    "action": action
                }
        elif action == "speak":
            text = kwargs.get("text", "")
            if not text:
                return {"success": False, "error": "text required"}
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                return {"success": True, "output": f"Spoke: {text[:50]}"}
            except ImportError:
                return {
                    "success": False,
                    "error": "pyttsx3 not installed. Run: pip install pyttsx3",
                    "action": action
                }
        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: transcribe, speak"}

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

