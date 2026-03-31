import os
import logging
import requests
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ImageGenTool:
    """
    Инструмент для генерации изображений с использованием бесплатных API.
    По умолчанию использует Pollinations.ai для создания визуального контента.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "image_gen",
            "description": "Генерация изображений по текстовому описанию (бесплатно).",
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
        try:
            width = kwargs.get("width", 1024)
            height = kwargs.get("height", 1024)
            seed = kwargs.get("seed", uuid.uuid4().int % 1000000)
            model = kwargs.get("model", "flux")
            
            # Использование Pollinations.ai API (полностью бесплатно и без ключа)
            # URL format: https://pollinations.ai/p/{prompt}?width={width}&height={height}&seed={seed}&model={model}
            encoded_prompt = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&model={model}"
            
            # Сохранение изображения
            output_dir = "generated_images"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"image_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(output_dir, filename)
            
            response = requests.get(url)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                
                return {
                    "success": True,
                    "url": url,
                    "local_path": filepath,
                    "message": f"Изображение успешно сгенерировано по промпту: {prompt}"
                }
            else:
                return {"success": False, "error": f"Ошибка API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Ошибка ImageGenTool: {e}")
            return {"success": False, "error": str(e)}
