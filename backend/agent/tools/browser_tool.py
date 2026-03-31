import asyncio
import logging
from typing import Dict, Any, Optional
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

class BrowserTool:
    """
    Инструмент для автоматизации браузера с использованием Playwright.
    Обеспечивает веб-навигацию, извлечение данных и взаимодействие с элементами.
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "browser",
            "description": "Автоматизация браузера: навигация, поиск, извлечение данных.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "search", "click", "type", "screenshot", "extract_text"],
                        "description": "Действие для выполнения"
                    },
                    "url": {"type": "string", "description": "URL для навигации"},
                    "query": {"type": "string", "description": "Поисковый запрос или текст для ввода"},
                    "selector": {"type": "string", "description": "CSS селектор для клика или ввода"}
                },
                "required": ["action"]
            }
        }

    async def _ensure_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright не установлен. Установите его с помощью 'pip install playwright' и 'playwright install'")
        
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        try:
            await self._ensure_browser()
            
            if action == "navigate":
                url = kwargs.get("url")
                if not url:
                    return {"success": False, "error": "URL не указан"}
                await self.page.goto(url)
                return {"success": True, "url": self.page.url, "title": await self.page.title()}
            
            elif action == "search":
                query = kwargs.get("query")
                if not query:
                    return {"success": False, "error": "Запрос не указан"}
                # Пример поиска в Google
                await self.page.goto(f"https://www.google.com/search?q={query}")
                results = await self.page.inner_text("body")
                return {"success": True, "content": results[:1000] + "..."}
                
            elif action == "extract_text":
                content = await self.page.inner_text("body")
                return {"success": True, "content": content}
                
            elif action == "screenshot":
                path = kwargs.get("path", "screenshot.png")
                await self.page.screenshot(path=path)
                return {"success": True, "path": path}
                
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
                
        except Exception as e:
            logger.error(f"Ошибка BrowserTool: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
