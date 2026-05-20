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
    По умолчанию использует Gemini 3.1 Flash Image (Nano Banana 2) при наличии GOOGLE_API_KEY,
    с автоматическим откатом на бесплатный Pollinations.ai (Flux) при его отсутствии или ошибках.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "image_gen",
            "description": "Генерация высококачественных изображений по текстовому описанию с использованием Gemini 3.1 (Nano Banana 2) или бесплатного резервного API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Текстовое описание изображения"},
                    "width": {"type": "integer", "description": "Ширина изображения", "default": 1024},
                    "height": {"type": "integer", "description": "Высота изображения", "default": 1024},
                    "seed": {"type": "integer", "description": "Случайное число для генерации"},
                    "model": {"type": "string", "description": "Модель для генерации при откате (flux, turbo и др.)", "default": "flux"}
                },
                "required": ["prompt"]
            }
        }

    async def execute(self, prompt: str, **kwargs) -> Dict[str, Any]:
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        seed = kwargs.get("seed", uuid.uuid4().int % 1000000)
        model = kwargs.get("model", "flux")
        
        # 1. Попытка использовать Google Gemini 3.1 Flash Image (Nano Banana 2)
        api_key = settings.GOOGLE_API_KEY
        if api_key:
            try:
                logger.info("Использование Google Gemini 3.1 Flash Image API (Nano Banana 2)")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
                
                aspect_ratio = get_aspect_ratio(width, height)
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "imageConfig": {
                            "aspectRatio": aspect_ratio
                        }
                    }
                }
                
                response = requests.post(
                    url, 
                    json=payload, 
                    headers={"Content-Type": "application/json"}, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            inline_data = parts[0].get("inlineData", {})
                            image_base64 = inline_data.get("data")
                            if image_base64:
                                output_dir = "generated_images"
                                os.makedirs(output_dir, exist_ok=True)
                                filename = f"image_{uuid.uuid4().hex[:8]}.png"
                                filepath = os.path.join(output_dir, filename)
                                
                                with open(filepath, "wb") as f:
                                    f.write(base64.b64decode(image_base64))
                                    
                                return {
                                    "success": True,
                                    "url": f"local:{filepath}",
                                    "local_path": filepath,
                                    "message": f"Изображение успешно сгенерировано с помощью Gemini 3.1 Flash Image по промпту: {prompt}"
                                }
                logger.warning(f"Ошибка Gemini API ({response.status_code}): {response.text}. Откат на Pollinations.ai.")
            except Exception as e:
                logger.error(f"Не удалось сгенерировать изображение через Gemini API: {e}. Откат на Pollinations.ai.")

        # 2. Резервный вариант: бесплатный API Pollinations.ai
        try:
            logger.info("Использование резервного API Pollinations.ai")
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
                    "message": f"Изображение успешно сгенерировано через резервный API (Flux) по промпту: {prompt}"
                }
            else:
                return {"success": False, "error": f"Ошибка резервного API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Ошибка ImageGenTool (резервный API): {e}")
            return {"success": False, "error": str(e)}
