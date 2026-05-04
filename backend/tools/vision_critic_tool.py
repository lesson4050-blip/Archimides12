import logging
from typing import Dict, Any
from backend.agent.vision_feedback import VisionFeedbackLoop

logger = logging.getLogger(__name__)

class VisionCriticTool:
    """
    Visual Grounding Tool. Gives Archimedes Manus-level web perception.
    The agent can ask the Vision model to look at a URL (e.g. localhost)
    and report back exact structural, visual, and layout bugs.
    """
    
    def __init__(self, router):
        self.router = router
        self.vision_loop = VisionFeedbackLoop(router=router)

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "vision_critic",
                "description": (
                    "Look at a web page and report visual bugs (UI/UX). "
                    "Use this after starting a frontend dev server to VERIFY your changes visually. "
                    "It will find overlapping text, broken CSS, missing images, and misalignment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to inspect (e.g., http://localhost:3000)"
                        },
                        "context": {
                            "type": "string",
                            "description": "What you expect to see on this page (e.g., 'A login form with blue button')."
                        }
                    },
                    "required": ["url", "context"]
                }
            }
        }

    async def execute(self, session_id: str, url: str, context: str, **kwargs) -> Dict[str, Any]:
        try:
            # Note: We assume the sandbox exposes localhost correctly to the host, 
            # or the URL is accessible from the host.
            # If the URL is localhost, we might need to map it to the sandbox IP.
            # For simplicity, we just pass the URL to the VisionFeedbackLoop.
            
            logger.info(f"👁️ Vision Critic inspecting: {url}")
            
            result = await self.vision_loop.analyze_url(url=url, context=context)
            
            if not result.get("analyzed"):
                return {
                    "success": False, 
                    "error": result.get("reason", "Vision analysis failed or dependencies missing.")
                }
                
            if result.get("has_problems"):
                problems = result.get("problems", [])
                formatted_problems = "\n".join([f"- [{p.get('severity')}] {p.get('type')}: {p.get('fix')} (At: {p.get('location')})" for p in problems])
                return {
                    "success": True,
                    "quality_score": result.get("quality_score"),
                    "output": f"Visual bugs detected! Fix them before proceeding:\n{formatted_problems}"
                }
            else:
                return {
                    "success": True,
                    "quality_score": result.get("quality_score"),
                    "output": f"Visual check PASSED! Page looks exactly as intended. Summary: {result.get('summary')}"
                }
                
        except Exception as e:
            logger.error(f"Vision Critic error: {e}")
            return {"success": False, "error": str(e)}
