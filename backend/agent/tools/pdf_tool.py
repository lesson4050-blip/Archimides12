import os
import logging
from typing import Dict, Any, List, Optional
try:
    import PyPDF2
    from pdf2image import convert_from_path
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFTool:
    """
    Инструмент для обработки PDF документов.
    Обеспечивает чтение текста, конвертацию в изображения и объединение PDF.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "pdf",
            "description": "Обработка PDF документов: чтение текста, конвертация в изображения.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read_text", "to_images", "merge", "info"],
                        "description": "Действие для выполнения"
                    },
                    "path": {"type": "string", "description": "Путь к PDF файлу"},
                    "output_dir": {"type": "string", "description": "Директория для сохранения изображений"},
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "Список путей для объединения"}
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        if not PDF_AVAILABLE:
            return {"success": False, "error": "Библиотеки PyPDF2 или pdf2image не установлены. Установите их с помощью 'pip install PyPDF2 pdf2image'"}
            
        try:
            path = kwargs.get("path")
            
            if action == "read_text":
                if not path or not os.path.exists(path):
                    return {"success": False, "error": f"Файл не найден: {path}"}
                
                text = ""
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                
                return {"success": True, "content": text, "pages": len(reader.pages)}
                
            elif action == "to_images":
                if not path or not os.path.exists(path):
                    return {"success": False, "error": f"Файл не найден: {path}"}
                
                output_dir = kwargs.get("output_dir", "pdf_images")
                os.makedirs(output_dir, exist_ok=True)
                
                images = convert_from_path(path)
                image_paths = []
                for i, image in enumerate(images):
                    img_path = os.path.join(output_dir, f"page_{i+1}.png")
                    image.save(img_path, "PNG")
                    image_paths.append(img_path)
                
                return {"success": True, "image_paths": image_paths, "count": len(image_paths)}
                
            elif action == "info":
                if not path or not os.path.exists(path):
                    return {"success": False, "error": f"Файл не найден: {path}"}
                
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    info = reader.metadata
                    return {
                        "success": True, 
                        "pages": len(reader.pages),
                        "author": info.author if info else "Unknown",
                        "creator": info.creator if info else "Unknown",
                        "producer": info.producer if info else "Unknown",
                        "subject": info.subject if info else "Unknown",
                        "title": info.title if info else "Unknown"
                    }
            
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
                
        except Exception as e:
            logger.error(f"Ошибка PDFTool: {e}")
            return {"success": False, "error": str(e)}
