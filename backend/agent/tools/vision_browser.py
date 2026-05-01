from typing import Dict, Any, Optional
import logging
import asyncio
import base64

logger = logging.getLogger(__name__)

class VisionBrowserTool:
    """
    Инструмент для визуального анализа страниц и интерфейсов через Gemini Vision.
    Принимает URL, делает скриншот через Playwright, и скармливает его Gemini.
    """
    def __init__(self):
        self.name = "vision_browser"
        self.description = "Открывает URL, делает скриншот и анализирует страницу с помощью vision-модели. Полезно для визуального тестирования верстки."

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "vision_browser",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the page to analyze"
                        },
                        "instructions": {
                            "type": "string",
                            "description": "What to look for or analyze in the screenshot."
                        }
                    },
                    "required": ["url", "instructions"]
                }
            }
        }

    async def execute(self, url: str, instructions: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"VisionBrowserTool: analyzing {url}")
        
        try:
            # Import dynamically to avoid heavy startup penalty
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                context = await browser.new_context(viewport={'width': 1280, 'height': 800})
                page = await context.new_page()
                
                await page.goto(url, wait_until="networkidle")
                
                screenshot_bytes = await page.screenshot(full_page=True)
                await browser.close()
                
            image_data = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            import google.generativeai as genai
            from backend.config import settings
            
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = await asyncio.to_thread(
                model.generate_content,
                [
                    {
                        "mime_type": "image/png",
                        "data": image_data
                    },
                    instructions
                ]
            )
            
            return {
                "success": True,
                "url": url,
                "analysis": response.text,
                "screenshot_size_bytes": len(screenshot_bytes)
            }
            
        except Exception as e:
            logger.error(f"VisionBrowserTool error: {e}")
            return {"success": False, "error": str(e)}
