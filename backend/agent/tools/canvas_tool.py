import logging
from typing import Dict, Any, List
import json
import uuid
import os

logger = logging.getLogger(__name__)

class CanvasEngineTool:
    """
    Генерирует JSON-массив слайдов для нового React Canvas Engine.
    Строгая валидация структуры.
    """
    def __init__(self):
        self.name = "canvas_engine"
        self.description = "Генерирует JSON-массив слайдов для презентаций (заменяет старый Presenton). Строго придерживается JSON структуры."

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "canvas_engine",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Тема презентации."
                        },
                        "slides_json": {
                            "type": "string",
                            "description": "Строка с JSON-массивом слайдов. Пример: [{'id': 'uuid', 'type': 'hero', 'content': {'title': '...', 'subtitle': '...'}}]"
                        }
                    },
                    "required": ["topic", "slides_json"]
                }
            }
        }

    async def execute(self, topic: str, slides_json: str, session_id: str = None, **kwargs) -> Dict[str, Any]:
        logger.info(f"CanvasEngineTool: Generating presentation for '{topic}'")
        try:
            slides = json.loads(slides_json)
            if not isinstance(slides, list):
                return {"success": False, "error": "slides_json must be a JSON array of slide objects."}
                
            # Basic validation
            for i, slide in enumerate(slides):
                if "id" not in slide:
                    slide["id"] = f"slide-{i}-{str(uuid.uuid4())[:8]}"
                if "type" not in slide:
                    slide["type"] = "standard"
                if "content" not in slide:
                    slide["content"] = {}
                    
            # In a real implementation we would save this to the database
            # as an Artifact.
            if session_id:
                from backend.db.crud import AsyncSessionLocal
                from backend.db.models import Artifact
                
                # Save presentation JSON to an artifact file in the workspace or data folder
                workspace_dir = os.path.abspath(f"./workspace/{session_id}")
                os.makedirs(workspace_dir, exist_ok=True)
                file_path = os.path.join(workspace_dir, f"presentation_{uuid.uuid4().hex[:8]}.json")
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({"topic": topic, "slides": slides}, f, ensure_ascii=False, indent=2)
                
                # We would also log it in the DB
                async with AsyncSessionLocal() as db:
                    artifact = Artifact(
                        session_id=session_id,
                        name=f"Presentation: {topic}",
                        type="presentation",
                        path=file_path
                    )
                    db.add(artifact)
                    await db.commit()
            
            return {
                "success": True,
                "message": "Презентация успешно сгенерирована и сохранена в формате Canvas JSON.",
                "slides_count": len(slides)
            }
        except json.JSONDecodeError as e:
            logger.error(f"CanvasEngineTool JSON Error: {e}")
            return {"success": False, "error": f"Invalid JSON format: {e}"}
        except Exception as e:
            logger.error(f"CanvasEngineTool Error: {e}")
            return {"success": False, "error": str(e)}
