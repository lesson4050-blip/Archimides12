"""
COSMO Presentation — Native Archimedes Tool
Generates Gamma/Kimi quality PPTX presentations.
Works exactly like browser_tool or shell_tool — always available,
no external dependencies for the agent.
"""
import asyncio
import httpx
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.cosmo.engine import get_engine_url, start_engine

logger = logging.getLogger(__name__)

# Where generated PPTX files are saved for download
OUTPUT_DIR = Path(os.environ.get(
    "COSMO_OUTPUT_DIR",
    "/home/ubuntu/workspace/presentations"
))


class CosmoPresentationTool:
    """
    Native presentation generator. Always available to the agent.
    Produces professional PPTX at Gamma/Kimi level quality.
    """

    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "presentation",
                "description": (
                    "Generate professional AI presentations (PPTX). "
                    "Gamma/Kimi level quality with real images and themes. "
                    "ALWAYS use this for: pitch decks, business slides, "
                    "educational presentations, reports as slides, "
                    "any request for 'презентация', 'слайды', 'deck'. "
                    "Returns downloadable PPTX file."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "What to create a presentation about. "
                                "Be specific: include topic, audience, "
                                "key points, tone (formal/creative/etc)."
                            )
                        },
                        "slide_count": {
                            "type": "integer",
                            "description": (
                                "Number of slides. Default: 8. "
                                "Min: 5. Max: 20."
                            )
                        },
                        "theme": {
                            "type": "string",
                            "enum": [
                                "dark", "light", "navy", "corporate",
                                "minimal", "bold", "emerald",
                                "rose", "gradient"
                            ],
                            "description": (
                                "Visual theme. "
                                "dark — premium dark OLED (default). "
                                "corporate — professional business. "
                                "minimal — clean whitespace. "
                                "bold — high contrast modern."
                            )
                        },
                        "language": {
                            "type": "string",
                            "description": (
                                "Output language. "
                                "ru for Russian (default), en for English."
                            )
                        },
                        "outline": {
                            "type": "array",
                            "description": (
                                "Optional: pre-defined slide structure. "
                                "If provided, skips outline generation. "
                                "Format: [{title, points: []}]"
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "points": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "filename": {
                            "type": "string",
                            "description": (
                                "Output filename without extension. "
                                "Default: auto-generated from topic."
                            )
                        }
                    },
                    "required": ["prompt"]
                }
            }
        }

    async def execute(
        self,
        prompt: str,
        slide_count: int = 8,
        theme: str = "dark",
        language: str = "ru",
        outline: List[Dict] = None,
        filename: str = None,
        session_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:

        if not prompt:
            return {"success": False, "error": "prompt is required"}

        # Ensure engine is running
        engine_url = get_engine_url()
        if not await self._ping(engine_url):
            logger.info("COSMO engine not running, starting...")
            started = await start_engine()
            if not started:
                return {
                    "success": False,
                    "error": (
                        "COSMO Presentation engine failed to start. "
                        "Check that cosmo_engine_core/ exists and "
                        "requirements are installed."
                    )
                }

        slide_count = min(max(slide_count, 5), 20)

        # Generate filename
        if not filename:
            safe = "".join(
                c for c in prompt[:40] if c.isalnum() or c in " _-"
            ).strip().replace(" ", "_")
            filename = f"cosmo_{safe}" if safe else "cosmo_presentation"

        output_path = OUTPUT_DIR / f"{filename}.pptx"

        try:
            async with httpx.AsyncClient(timeout=180) as c:

                # STEP 1: Generate or use provided outline
                if outline:
                    presentation_id = await self._create_from_outline(
                        c, engine_url, prompt, outline, theme, language
                    )
                else:
                    # Generate outline first (Kimi-style workflow)
                    logger.info(f"COSMO: generating outline for '{prompt[:50]}'")
                    presentation_id = await self._generate_outline(
                        c, engine_url, prompt, slide_count, language
                    )

                if not presentation_id:
                    return {
                        "success": False,
                        "error": "Failed to generate presentation outline"
                    }

                # STEP 2: Generate slides from outline
                logger.info(
                    f"COSMO: generating slides "
                    f"(id={presentation_id}, theme={theme})"
                )
                ok = await self._generate_slides(
                    c, engine_url, presentation_id, theme
                )
                if not ok:
                    return {
                        "success": False,
                        "error": "Slide generation failed"
                    }

                # STEP 3: Download PPTX
                logger.info(f"COSMO: downloading PPTX to {output_path}")
                downloaded = await self._download_pptx(
                    c, engine_url, presentation_id, output_path
                )
                if not downloaded:
                    return {
                        "success": False,
                        "error": "Failed to download PPTX file"
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": (
                    "Generation timeout. "
                    "Try fewer slides or a simpler prompt."
                )
            }
        except Exception as e:
            logger.error(f"COSMO tool error: {e}")
            return {"success": False, "error": str(e)}

        # STEP 4: Copy to sandbox workspace for download
        try:
            sandbox_path = (
                f"/home/ubuntu/workspace/{output_path.name}"
            )
            import shutil
            shutil.copy2(str(output_path), sandbox_path)
        except Exception:
            sandbox_path = str(output_path)

        file_size_kb = output_path.stat().st_size // 1024

        return {
            "success": True,
            "output": (
                f"✅ COSMO Presentation готова!\n\n"
                f"📊 Тема: {prompt[:60]}\n"
                f"🎨 Стиль: {theme}\n"
                f"📁 Файл: {output_path.name} ({file_size_kb} KB)\n"
                f"📥 Путь: {sandbox_path}\n\n"
                f"Файл сохранён и готов к скачиванию."
            ),
            "file_path": sandbox_path,
            "filename": output_path.name,
            "file_size_kb": file_size_kb,
            "presentation_id": presentation_id,
            "preview_url": (
                f"{engine_url}/presentation/{presentation_id}"
            )
        }

    async def _ping(self, engine_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                r = await c.get(f"{engine_url}/api/health")
                return r.status_code == 200
        except Exception:
            return False

    async def _generate_outline(
        self,
        c: httpx.AsyncClient,
        engine_url: str,
        prompt: str,
        slide_count: int,
        language: str
    ) -> Optional[str]:
        try:
            r = await c.post(
                f"{engine_url}/api/v1/ppt/generate-outline",
                json={
                    "prompt": prompt,
                    "slide_count": slide_count,
                    "language": language
                },
                timeout=60
            )
            if r.status_code == 200:
                return r.json().get("id")
            logger.error(f"Outline error {r.status_code}: {r.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return None

    async def _create_from_outline(
        self,
        c: httpx.AsyncClient,
        engine_url: str,
        title: str,
        outline: List[Dict],
        theme: str,
        language: str
    ) -> Optional[str]:
        try:
            r = await c.post(
                f"{engine_url}/api/v1/ppt/create-from-outline",
                json={
                    "title": title,
                    "outline": outline,
                    "theme": theme,
                    "language": language
                },
                timeout=60
            )
            if r.status_code == 200:
                return r.json().get("id")
            return None
        except Exception as e:
            logger.error(f"Create from outline failed: {e}")
            return None

    async def _generate_slides(
        self,
        c: httpx.AsyncClient,
        engine_url: str,
        presentation_id: str,
        theme: str
    ) -> bool:
        try:
            r = await c.post(
                f"{engine_url}/api/v1/ppt/generate-presentation",
                json={
                    "id": presentation_id,
                    "theme": theme,
                    "fetch_images": True
                },
                timeout=150
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Slide generation failed: {e}")
            return False

    async def _download_pptx(
        self,
        c: httpx.AsyncClient,
        engine_url: str,
        presentation_id: str,
        output_path: Path
    ) -> bool:
        try:
            r = await c.get(
                f"{engine_url}/api/v1/ppt/download/{presentation_id}",
                timeout=30
            )
            if r.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(r.content)
                return True
            logger.error(
                f"Download failed {r.status_code}: {r.text[:100]}"
            )
            return False
        except Exception as e:
            logger.error(f"PPTX download failed: {e}")
            return False
