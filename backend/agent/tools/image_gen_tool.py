import os
import logging
import requests
import uuid
import base64
from typing import Dict, Any
from backend.config import settings

logger = logging.getLogger(__name__)

def get_aspect_ratio(width: int, height: int) -> str:
    """Helper to map width and height to Gemini supported aspect ratios."""
    if height == 0:
        return "1:1"
    ratio = width / height
    if abs(ratio - 1.0) < 0.1:
        return "1:1"
    elif abs(ratio - (16/9)) < 0.1:
        return "16:9"
    elif abs(ratio - (9/16)) < 0.1:
        return "9:16"
    elif abs(ratio - (4/3)) < 0.1:
        return "4:3"
    elif abs(ratio - (3/4)) < 0.1:
        return "3:4"
    elif ratio > 1.0:
        return "16:9"
    else:
        return "9:16"

class ImageGenTool:
    """
    Инструмент для генерации изображений.
    Использует API Pollinations.ai (Flux) для генерации высококачественных изображений.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "image_gen",
            "description": "Генерация высококачественных изображений по текстовому описанию с использованием API Pollinations.ai (Flux).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Текстовое описание изображения"},
                    "width": {"type": "integer", "description": "Ширина изображения", "default": 1024},
                    "height": {"type": "integer", "description": "Высота изображения", "default": 1024},
                    "seed": {"type": "integer", "description": "Случайное число для генерации"},
                    "model": {"type": "string", "description": "Модель для генерации (flux, turbo и др.)", "default": "flux"}
                },
                "required": ["prompt"]
            }
        }

    async def execute(self, prompt: str, **kwargs) -> Dict[str, Any]:
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        seed = kwargs.get("seed", uuid.uuid4().int % 1000000)
        model = kwargs.get("model", "flux")
        
        # Используем API Pollinations.ai для генерации изображений
        try:
            logger.info("Использование API Pollinations.ai")
            encoded_prompt = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&model={model}"
            
            output_dir = "generated_images"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"image_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(output_dir, filename)
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                
                return {
                    "success": True,
                    "url": url,
                    "local_path": filepath,
                    "message": f"Изображение успешно сгенерировано через Pollinations.ai (Flux) по промпту: {prompt}"
                }
            else:
                return {"success": False, "error": f"Ошибка API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Ошибка ImageGenTool: {e}")
            return {"success": False, "error": str(e)}
