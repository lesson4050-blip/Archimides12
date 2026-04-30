"""
Vision Tool — screenshot analysis via Gemini Vision.
Takes a screenshot of the sandbox desktop, sends to Gemini Pro Vision,
returns structured analysis. Critical for GUI automation tasks.
"""
import base64
import logging
import os
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VisionTool:
    """Screenshot → Gemini Vision → structured solution."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "vision",
                "description": (
                    "Take a screenshot of the current desktop/browser state, "
                    "analyze it with AI vision, and answer questions about what "
                    "is visible. Use when you need to see the current UI state, "
                    "find elements on screen, or verify visual results."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": (
                                "What to look for or analyze in the screenshot. "
                                "E.g. 'What button should I click to submit?', "
                                "'Is the chart rendered correctly?', "
                                "'What error message is shown?'"
                            )
                        },
                        "screenshot_path": {
                            "type": "string",
                            "description": (
                                "Optional: path to an existing screenshot file. "
                                "If not provided, a new screenshot is taken."
                            )
                        }
                    },
                    "required": ["question"]
                }
            }
        }

    async def execute(
        self,
        question: str,
        screenshot_path: str = None,
        session_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        import google.generativeai as genai
        from backend.config import settings

        try:
            if not screenshot_path:
                import tempfile
                fd, screenshot_path = tempfile.mkstemp(suffix=".png", prefix=f"vision_{session_id or 'default'}_")
                os.close(fd)
                result = subprocess.run(
                    ["scrot", "-z", screenshot_path],
                    capture_output=True, timeout=10
                )
                if result.returncode != 0:
                    # Fallback: try import
                    result = subprocess.run(
                        ["import", "-window", "root", screenshot_path],
                        capture_output=True, timeout=10
                    )

            if not os.path.exists(screenshot_path):
                return {
                    "success": False,
                    "error": "Could not capture screenshot. "
                             "Is the display available?"
                }

            # Read and encode image
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            # Call Gemini Vision
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")

            response = model.generate_content([
                {
                    "mime_type": "image/png",
                    "data": image_data
                },
                (
                    f"Analyze this screenshot and answer: {question}\n\n"
                    "Be specific and actionable. If you see UI elements, "
                    "describe their exact position and text. "
                    "If you see errors, quote them exactly."
                )
            ])

            analysis = response.text
            return {
                "success": True,
                "output": analysis,
                "screenshot_path": screenshot_path
            }

        except Exception as e:
            logger.error(f"VisionTool error: {e}")
            return {"success": False, "error": str(e)}
