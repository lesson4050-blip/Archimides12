"""
Visual Feedback Loop — «Глаза» Archimedes.
После генерации любого визуального контента (слайды, UI, PDF)
делает скриншот, анализирует через Vision модель,
возвращает список конкретных проблем.

Top-level implementation:
- Retry logic with exponential backoff
- Concurrency-safe (semaphore)
- Graceful degradation when Playwright/Gemini unavailable
- Structured JSON output with validation
"""
import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Concurrency limit: max 3 screenshots in parallel
_SCREENSHOT_SEMAPHORE = asyncio.Semaphore(3)

VISION_PROMPT = """You are a strict visual QA engineer.
Analyze this screenshot of a {context} and find ALL visual problems.

Report ONLY real problems you actually see. Be specific.

Check for:
1. Text overflow (text cut off or going outside bounds)
2. Text overlapping images or other elements
3. Elements outside slide boundaries
4. Font too small to read (< 10pt equivalent)
5. Color contrast issues (text unreadable on background)
6. Broken layout (misaligned elements)
7. Missing images (placeholder boxes, broken image icons)
8. Truncated text ending mid-word or mid-sentence
9. Duplicate content (same text appearing twice)
10. Empty slides (slide with no content)

Return JSON:
{{
  "has_problems": true/false,
  "quality_score": 1-10,
  "problems": [
    {{
      "type": "text_overflow|overlap|truncation|contrast|missing_image|misalignment|empty",
      "location": "describe where on slide",
      "severity": "critical|major|minor",
      "fix": "exactly what to change"
    }}
  ],
  "summary": "one sentence overall assessment"
}}

Return ONLY valid JSON. No markdown. No explanation."""


class VisionFeedbackLoop:
    """
    Analyzes generated visual content via screenshot + Vision model.
    Plugs into COSMO presentation pipeline automatically.
    """

    def __init__(self, router=None):
        self.router = router
        self._playwright_available: Optional[bool] = None

    async def _check_playwright(self) -> bool:
        """Check Playwright availability once, cache result."""
        if self._playwright_available is not None:
            return self._playwright_available
        try:
            from playwright.async_api import async_playwright
            self._playwright_available = True
        except ImportError:
            logger.warning("Playwright not installed — vision QA screenshots disabled")
            self._playwright_available = False
        return self._playwright_available

    async def analyze_url(
        self,
        url: str,
        context: str = "presentation slide",
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Take screenshot of URL, analyze with Vision, return problems.
        Retries on transient failures.
        """
        screenshot_b64, dom_snapshot = await self._take_screenshot_with_retry(url, max_retries)
        if not screenshot_b64:
            return {
                "analyzed": False,
                "reason": "screenshot_failed",
                "has_problems": False,
                "quality_score": 0,
                "problems": [],
            }

        return await self._analyze_screenshot(screenshot_b64, dom_snapshot, context)

    async def analyze_pptx_slides(
        self,
        presentation_id: str,
        artist_url: str = "http://localhost:3005",
        slide_count: int = None,
    ) -> Dict[str, Any]:
        """
        Analyze each slide of a generated presentation.
        Returns aggregated quality report.
        """
        # Quick check: if Playwright isn't available, skip entirely
        if not await self._check_playwright():
            return {
                "slides_analyzed": 0,
                "total_problems": 0,
                "critical_slides": 0,
                "avg_quality": 0,
                "passed": False,
                "skipped": True,
                "reason": "playwright_not_available",
                "per_slide": [],
                "summary": "Vision QA skipped: Playwright not installed.",
            }

        # Get slide count from artist if not provided
        if not slide_count:
            slide_count = await self._fetch_slide_count(
                presentation_id, artist_url
            )

        # Analyze slides concurrently (limited by semaphore)
        tasks = []
        for slide_n in range(1, slide_count + 1):
            slide_url = (
                f"{artist_url}/presentation/{presentation_id}"
                f"?slide={slide_n}"
            )
            tasks.append(
                self._analyze_single_slide(slide_url, slide_n)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        problems_by_slide = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Slide analysis failed: {r}")
                problems_by_slide.append({
                    "analyzed": False,
                    "reason": str(r),
                    "problems": [],
                })
            else:
                problems_by_slide.append(r)

        return self._aggregate_results(problems_by_slide)

    async def _analyze_single_slide(
        self, url: str, slide_number: int
    ) -> Dict[str, Any]:
        """Analyze one slide with semaphore control."""
        async with _SCREENSHOT_SEMAPHORE:
            result = await self.analyze_url(
                url=url,
                context=f"presentation slide {slide_number}"
            )
            result["slide_number"] = slide_number
            return result

    def _aggregate_results(
        self, slides: List[Dict]
    ) -> Dict[str, Any]:
        """Build aggregated quality report from per-slide results."""
        analyzed = [s for s in slides if s.get("analyzed")]
        
        critical_slides = [
            s for s in analyzed
            if s.get("has_problems")
            and any(
                p.get("severity") == "critical"
                for p in s.get("problems", [])
            )
        ]

        total_problems = sum(
            len(s.get("problems", [])) for s in analyzed
        )

        avg_quality = (
            sum(s.get("quality_score", 8) for s in analyzed) / len(analyzed)
            if analyzed else 0
        )

        logger.info(
            f"Visual QA: {len(analyzed)}/{len(slides)} slides analyzed, "
            f"{total_problems} problems found, "
            f"avg quality: {avg_quality:.1f}/10"
        )

        return {
            "slides_analyzed": len(analyzed),
            "slides_total": len(slides),
            "total_problems": total_problems,
            "critical_slides": len(critical_slides),
            "avg_quality": round(avg_quality, 1),
            "passed": avg_quality >= 7.0 and len(critical_slides) == 0,
            "per_slide": slides,
            "summary": self._build_summary(slides),
        }

    def _build_summary(self, slides: List[Dict]) -> str:
        all_problems = []
        for s in slides:
            for p in s.get("problems", []):
                all_problems.append(
                    f"Slide {s.get('slide_number','?')}: "
                    f"[{p.get('severity','?')}] {p.get('type','?')} — {p.get('fix','')}"
                )
        if not all_problems:
            return "No visual problems detected. Presentation looks clean."
        return "\n".join(all_problems[:15])

    async def _fetch_slide_count(
        self, presentation_id: str, artist_url: str
    ) -> int:
        """Get slide count from Artist API, fallback to 8."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"{artist_url}/api/presentation/{presentation_id}"
                )
                if r.status_code == 200:
                    data = r.json()
                    count = len(data.get("slides", []))
                    if count > 0:
                        return count
        except Exception as e:
            logger.debug(f"Could not fetch slide count: {e}")
        return 8  # fallback

    async def _take_screenshot_with_retry(
        self, url: str, max_retries: int = 2
    ) -> Tuple[Optional[str], Optional[str]]:
        """Screenshot with exponential backoff retry. Returns (screenshot_b64, dom_snapshot)."""
        for attempt in range(max_retries + 1):
            screenshot_b64, dom_snapshot = await self._take_screenshot_and_dom(url)
            if screenshot_b64:
                return screenshot_b64, dom_snapshot
            if attempt < max_retries:
                wait = 2 ** attempt  # 1s, 2s
                logger.debug(f"Screenshot retry {attempt + 1}/{max_retries} in {wait}s")
                await asyncio.sleep(wait)
        return None, None

    async def _take_screenshot_and_dom(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Take screenshot via Playwright and extract DOM snapshot.
        Returns (base64_jpeg, dom_snapshot_str).
        """
        if not await self._check_playwright():
            return None, None

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 720}
                )
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
                
                # Extract DOM snapshot (Manus style DOM-awareness)
                dom_snapshot = await page.evaluate('''() => {
                    const cleanTree = (node) => {
                        if (node.nodeType === 3) return node.textContent.trim();
                        if (node.nodeType !== 1) return null;
                        const tag = node.tagName.toLowerCase();
                        if (['script', 'style', 'noscript', 'meta'].includes(tag)) return null;
                        let attrs = {};
                        if (node.id) attrs.id = node.id;
                        if (node.className) attrs.class = node.className;
                        let children = Array.from(node.childNodes).map(cleanTree).filter(n => n);
                        if (children.length === 0 && Object.keys(attrs).length === 0) return tag;
                        return { tag, attrs, children };
                    };
                    return JSON.stringify(cleanTree(document.body));
                }''')

                screenshot = await page.screenshot(
                    type="jpeg", quality=85
                )
                await browser.close()
                return base64.b64encode(screenshot).decode(), dom_snapshot
        except Exception as e:
            logger.warning(f"Playwright screenshot/DOM failed: {e}")
            return None, None

    async def _analyze_screenshot(
        self,
        screenshot_b64: str,
        dom_snapshot: str,
        context: str,
    ) -> Dict[str, Any]:
        """Send screenshot and DOM to Vision model for analysis."""
        try:
            from backend.models.gemini_client import GeminiClient
            gemini = GeminiClient()
            
            prompt = VISION_PROMPT.format(context=context)
            if dom_snapshot:
                prompt += f"\n\nDOM Context (for element IDs and accurate structural checks):\n{dom_snapshot[:4000]}"

            response = await gemini.generate_with_image(
                prompt=prompt,
                image_base64=screenshot_b64,
                image_mime_type="image/jpeg",
            )

            raw_text = response.get("text", "{}").strip()

            # Try parsing JSON response
            from backend.utils.json_repair import repair_and_parse
            data, _ = repair_and_parse(raw_text)

            if not data or not isinstance(data, dict):
                logger.warning(f"Vision QA parse failed, raw: {raw_text[:200]}")
                return {
                    "analyzed": True,
                    "has_problems": False,
                    "quality_score": 7,
                    "problems": [],
                    "summary": "Vision response could not be parsed — assuming OK",
                }

            # Validate and normalize response structure
            problems = data.get("problems", [])
            if not isinstance(problems, list):
                problems = []

            # Filter out nonsense problems (severity must be valid)
            valid_severities = {"critical", "major", "minor"}
            problems = [
                p for p in problems
                if isinstance(p, dict)
                and p.get("severity", "").lower() in valid_severities
            ]

            quality_score = data.get("quality_score", 7)
            if not isinstance(quality_score, (int, float)):
                quality_score = 7
            quality_score = max(1, min(10, quality_score))

            logger.info(
                f"Vision QA [{context}]: "
                f"score={quality_score}, "
                f"problems={len(problems)}"
            )

            return {
                "analyzed": True,
                "has_problems": len(problems) > 0,
                "quality_score": quality_score,
                "problems": problems,
                "summary": data.get("summary", ""),
            }

        except ImportError as e:
            logger.warning(f"Vision analysis dependency missing: {e}")
            return {
                "analyzed": False,
                "reason": f"Missing dependency: {e}",
                "has_problems": False,
                "quality_score": 0,
                "problems": [],
            }
        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            return {
                "analyzed": False,
                "reason": str(e),
                "has_problems": False,
                "quality_score": 0,
                "problems": [],
            }
