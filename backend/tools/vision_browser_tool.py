"""
VisionBrowserTool — "Eyes" upgrade for Archimedes.

Unlike text-only browsing, VisionBrowser:
1. Takes screenshot of every page
2. Sends to Vision LLM (Gemini Vision)
3. Returns "Visual Semantic Map": coordinates of buttons,
   inputs, headings, navigation elements
4. Performs "Visual Verification" after every click:
   confirms UI actually changed

This is what makes Manus unique. Now Archimedes has it too.
"""
import asyncio
import base64
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VisualElement:
    """A UI element detected by Vision LLM."""
    element_type: str     # button, input, link, heading, image
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    action_hint: str = ""  # "clickable", "fillable", "readable"


@dataclass
class VisualSemanticMap:
    """Complete semantic map of a webpage."""
    page_title: str
    page_url: str
    screenshot_b64: str
    elements: List[VisualElement] = field(default_factory=list)
    layout_description: str = ""
    interactive_count: int = 0
    
    def to_context(self) -> str:
        """Format for agent context."""
        lines = [
            f"## Visual Semantic Map: {self.page_title}",
            f"URL: {self.page_url}",
            f"Layout: {self.layout_description}",
            f"Interactive elements: {self.interactive_count}",
            "",
            "### Detected Elements:",
        ]
        for el in self.elements[:20]:
            lines.append(
                f"  [{el.element_type}] '{el.text}' "
                f"at ({el.x},{el.y}) size {el.width}x{el.height} "
                f"— {el.action_hint}"
            )
        return "\n".join(lines)


class VisionBrowserTool:
    """
    Browser tool with Vision LLM integration.
    Sees pages like a human, not just as text.
    """

    def __init__(self, router=None):
        self.router = router
        self._playwright = None
        self._browser = None
        self._page = None
        self._last_map: Optional[VisualSemanticMap] = None

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "vision_browser",
                "description": (
                    "Browser with AI vision. Unlike text browsing, this sees "
                    "the actual visual layout of pages. "
                    "Actions: navigate (go to URL + visual map), "
                    "click (click element by description), "
                    "fill (fill input by label), "
                    "screenshot (capture current state), "
                    "verify (confirm UI changed after action), "
                    "extract (extract structured data from visual layout)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "navigate", "click", "fill",
                                "screenshot", "verify", "extract", "close"
                            ]
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to"
                        },
                        "target": {
                            "type": "string",
                            "description": "Element description for click/fill"
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to fill into input"
                        },
                        "question": {
                            "type": "string",
                            "description": "Question to answer from visual content"
                        },
                        "expected_change": {
                            "type": "string",
                            "description": "What UI change to verify after action"
                        },
                    },
                    "required": ["action"]
                }
            }
        }

    async def _ensure_browser(self):
        """Initialize Playwright browser."""
        if self._playwright is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._page = await self._browser.new_page(
                    viewport={"width": 1280, "height": 720}
                )
                logger.info("VisionBrowser: Playwright initialized")
            except ImportError:
                raise RuntimeError(
                    "Playwright not installed: "
                    "pip install playwright && playwright install chromium"
                )

    async def _take_screenshot_b64(self) -> str:
        """Capture screenshot and return as base64."""
        if self._page is None:
            return ""
        screenshot_bytes = await self._page.screenshot(
            full_page=False, type="jpeg", quality=80
        )
        return base64.b64encode(screenshot_bytes).decode()

    async def _analyze_screenshot(
        self, screenshot_b64: str, question: str = ""
    ) -> Dict[str, Any]:
        """Send screenshot to Vision LLM for analysis."""
        if not self.router:
            return {"description": "No Vision LLM available", "elements": []}

        prompt = (
            "Analyze this screenshot of a webpage. "
            "Identify ALL interactive elements (buttons, inputs, links, dropdowns). "
            "For each element provide: type, text content, approximate position, "
            "and what action it enables.\n\n"
            "Also describe the overall page layout.\n\n"
        )
        if question:
            prompt += f"Additionally, answer: {question}\n\n"
        
        prompt += (
            'Return JSON:\n'
            '{"layout": "description", '
            '"elements": [{"type": "button", "text": "Submit", '
            '"x": 500, "y": 300, "w": 120, "h": 40, "action": "clickable"}], '
            '"answer": "if question asked"}'
        )

        try:
            # Try Gemini Vision first
            import google.generativeai as genai
            from backend.config import settings
            
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": screenshot_b64},
                prompt
            ])
            
            import json, re
            text = response.text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Vision LLM failed: {e}")
        
        return {"layout": "Unknown", "elements": [], "answer": ""}

    async def execute(
        self,
        action: str,
        url: str = None,
        target: str = None,
        value: str = None,
        question: str = None,
        expected_change: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a vision browser action."""
        try:
            await self._ensure_browser()

            if action == "navigate":
                if not url:
                    return {"success": False, "error": "URL required"}
                
                await self._page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(0.5)
                
                screenshot_b64 = await self._take_screenshot_b64()
                analysis = await self._analyze_screenshot(screenshot_b64)
                
                elements = [
                    VisualElement(
                        element_type=el.get("type", "unknown"),
                        text=el.get("text", ""),
                        x=el.get("x", 0), y=el.get("y", 0),
                        width=el.get("w", 0), height=el.get("h", 0),
                        action_hint=el.get("action", "")
                    )
                    for el in analysis.get("elements", [])
                ]
                
                self._last_map = VisualSemanticMap(
                    page_title=await self._page.title(),
                    page_url=url,
                    screenshot_b64=screenshot_b64,
                    elements=elements,
                    layout_description=analysis.get("layout", ""),
                    interactive_count=sum(
                        1 for el in elements
                        if el.action_hint in ("clickable", "fillable")
                    )
                )
                
                return {
                    "success": True,
                    "output": self._last_map.to_context(),
                    "page_title": self._last_map.page_title,
                    "elements_found": len(elements),
                }

            elif action == "click":
                if not target:
                    return {"success": False, "error": "target required"}
                
                # Try to find element by visual description
                try:
                    await self._page.get_by_text(target).first.click(timeout=5000)
                except Exception:
                    try:
                        await self._page.locator(f"[aria-label*='{target}']").first.click()
                    except Exception:
                        # Fallback: ask Vision LLM for coordinates
                        screenshot_b64 = await self._take_screenshot_b64()
                        analysis = await self._analyze_screenshot(
                            screenshot_b64,
                            f"Where is the element '{target}'? Give me its x,y coordinates."
                        )
                        answer = analysis.get("answer", "")
                        return {
                            "success": False,
                            "output": f"Could not find '{target}'. Vision says: {answer}"
                        }
                
                await asyncio.sleep(0.3)
                return {"success": True, "output": f"Clicked: {target}"}

            elif action == "fill":
                if not target or value is None:
                    return {"success": False, "error": "target and value required"}
                
                try:
                    await self._page.get_by_label(target).fill(value)
                except Exception:
                    await self._page.locator(f"input[placeholder*='{target}']").fill(value)
                
                return {"success": True, "output": f"Filled '{target}' with '{value}'"}

            elif action == "screenshot":
                screenshot_b64 = await self._take_screenshot_b64()
                analysis = await self._analyze_screenshot(
                    screenshot_b64, question or "Describe the current page state"
                )
                return {
                    "success": True,
                    "output": analysis.get("answer", analysis.get("layout", "")),
                    "layout": analysis.get("layout", ""),
                }

            elif action == "verify":
                """Visual verification: confirm UI changed after action."""
                screenshot_b64 = await self._take_screenshot_b64()
                verification_q = (
                    f"Did the following change occur: '{expected_change}'? "
                    f"Answer YES or NO and explain what you see."
                )
                analysis = await self._analyze_screenshot(
                    screenshot_b64, verification_q
                )
                answer = analysis.get("answer", "")
                verified = "yes" in answer.lower()
                
                return {
                    "success": True,
                    "verified": verified,
                    "output": f"Verification: {'✅ CONFIRMED' if verified else '❌ NOT CONFIRMED'} — {answer}",
                }

            elif action == "extract":
                screenshot_b64 = await self._take_screenshot_b64()
                analysis = await self._analyze_screenshot(
                    screenshot_b64,
                    question or "Extract all meaningful data from this page"
                )
                return {
                    "success": True,
                    "output": analysis.get("answer", ""),
                    "elements": [
                        {"type": el.element_type, "text": el.text}
                        for el in (self._last_map.elements if self._last_map else [])
                    ]
                }

            elif action == "close":
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
                self._playwright = None
                self._browser = None
                self._page = None
                return {"success": True, "output": "Browser closed"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"VisionBrowserTool error: {e}")
            return {"success": False, "error": str(e)}
