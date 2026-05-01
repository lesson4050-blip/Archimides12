"""
COSMO Presentation — Native Archimedes Tool
Generates Gamma/Kimi quality PPTX presentations.
Works exactly like browser_tool or shell_tool — always available,
no external dependencies for the agent.

Uses the real Presenton engine API:
  POST /api/v1/ppt/presentation/generate
"""
import httpx
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.cosmo.engine import get_engine_url, start_engine, ENGINE_DIR

logger = logging.getLogger(__name__)

# Where generated PPTX files are saved for download
OUTPUT_DIR = Path(os.environ.get(
    "COSMO_OUTPUT_DIR",
    str(Path(__file__).parent.parent.parent / "workspace" / "presentations")
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
                    "Gamma/Kimi level quality with rich content and themes. "
                    "ALWAYS use for: pitch decks, business slides, "
                    "educational presentations, reports as slides, "
                    "any request for 'презентация', 'слайды', 'deck'. "
                    "IMPORTANT: provide a DETAILED prompt with: topic context, "
                    "key points to cover, target audience, and purpose. "
                    "The richer the prompt, the better the presentation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "DETAILED description of what to present. Include: "
                                "1) Main topic and angle "
                                "2) Key points or sections to cover "
                                "3) Target audience "
                                "4) Purpose (pitch/education/report/etc). "
                                "The more detail, the better the result. "
                                "Example: 'Pitch deck for Archimedes AI agent: "
                                "cover problem, solution architecture (GraphRAG, Swarm, MCP), "
                                "competitive advantage vs Manus, market opportunity, "
                                "team and roadmap. Audience: tech investors.'"
                            )
                        },
                        "slide_count": {
                            "type": "integer",
                            "description": (
                                "Number of slides. Default: 8. "
                                "Min: 3. Max: 20."
                            )
                        },
                        "language": {
                            "type": "string",
                            "description": (
                                "Output language. "
                                "Russian (default), English, etc."
                            )
                        },
                        "template": {
                            "type": "string",
                            "enum": ["general", "modern", "standard", "swift"],
                            "description": (
                                "Visual template style. "
                                "general: clean professional (default). "
                                "modern: contemporary design. "
                                "standard: traditional layout. "
                                "swift: minimal fast-paced."
                            )
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
        prompt: str = None,
        slide_count: int = 8,
        language: str = "Russian",
        template: str = "general",   # general | modern | standard | swift
        filename: str = None,
        session_id: str = None,
        # Legacy kwargs compatibility
        topic: str = None,
        pages: int = None,
        **kwargs
    ) -> Dict[str, Any]:

        # Support legacy parameter names
        content = prompt or topic
        n_slides = slide_count if pages is None else pages

        if not content:
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

        n_slides = min(max(n_slides, 3), 20)

        # Generate filename
        if not filename:
            safe = "".join(
                c for c in content[:40] if c.isalnum() or c in " _-"
            ).strip().replace(" ", "_")
            filename = f"cosmo_{safe}" if safe else "cosmo_presentation"

        output_path = OUTPUT_DIR / f"{filename}.pptx"

        try:
            # Use the REAL Presenton API: POST /api/v1/ppt/presentation/generate
            async with httpx.AsyncClient(timeout=3600) as c:
                logger.info(
                    f"COSMO: generating presentation via "
                    f"/api/v1/ppt/presentation/generate "
                    f"(slides={n_slides}, lang={language})"
                )

                r = await c.post(
                    f"{engine_url}/api/v1/ppt/presentation/generate",
                    json={
                        "content": content,
                        "n_slides": n_slides,
                        "language": language,
                        "template": template,          # "general" | "modern" | "standard" | "swift"
                        "export_as": "pptx",
                        "include_title_slide": True,
                        "include_table_of_contents": n_slides >= 8,
                        # Quality multipliers
                        "tone": "professional",
                        "verbosity": "text-heavy",
                        "web_search": True,
                        "instructions": (
                            "TARGET QUALITY: Match Kimi K2.5 presentation quality level. "
                            "STRUCTURE: "
                            "- Include a table of contents slide as slide 2. "
                            "- Number all content slides (1.1, 1.2, 2.1, etc). "
                            "- Title slide must have subtitle and author/date area. "
                            "- Final slide must be conclusion/call-to-action. "
                            "CONTENT DENSITY: "
                            "- Every content slide needs: headline + 3-5 specific points + "
                            "  supporting detail for each point. "
                            "- Use real statistics, dates, and named examples. "
                            "- No generic statements. Every claim must be specific. "
                            "- Example: not 'AI is growing' but 'AI market reached $391B in 2025'. "
                            "DATA INTEGRITY: "
                            "- Percentages: -100% to +500% MAXIMUM. "
                            "- Never invent extreme values like -65000000%. "
                            "- Use organic numbers: 47.3%, not 50%. "
                            "IMAGES: "
                            "- Every content slide must request a specific, descriptive image. "
                            "- Be specific: 'space telescope observing distant galaxy' "
                            "  not just 'space'. "
                            "- Images must relate directly to slide content. "
                            "LANGUAGE: "
                            "- ALL text must be in the requested language. "
                            "- Never mix languages within a single presentation. "
                            "TYPOGRAPHY INTENT: "
                            "- Use serif font for main headings (editorial premium feel). "
                            "- Use sans-serif for body text. "
                            "- Section numbers in accent color. "
                            "TEXT QUALITY: "
                            "- End every paragraph at a complete sentence. "
                            "- Never cut text mid-word or mid-sentence. "
                            "- Speaker notes must summarize the key insight of each slide. "
                            "NEVER use markdown formatting like **bold** or _italic_ in the text fields!"
                        ),
                    },
                    timeout=3600
                )

                if r.status_code != 200:
                    error_text = r.text[:300]
                    logger.error(
                        f"COSMO generation failed "
                        f"({r.status_code}): {error_text}"
                    )
                    return {
                        "success": False,
                        "error": f"Engine returned {r.status_code}: {error_text}"
                    }

                result = r.json()
                # result contains: path, edit_path
                pptx_server_path = result.get("path", "")

                if pptx_server_path:
                    # pptx_server_path is absolute path like /app_data/exports/file.pptx
                    # The filename is the last part
                    pptx_filename = Path(pptx_server_path).name

                    # Try static mount first (fastest)
                    dl = await c.get(
                        f"{engine_url}/exports/{pptx_filename}",
                        timeout=30
                    )
                    if dl.status_code == 200:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(dl.content)
                    else:
                        # Fallback: read directly from filesystem
                        # (only works if engine runs on same machine, which it does)
                        engine_data_dir = ENGINE_DIR / "data" / "exports"
                        local_file = engine_data_dir / pptx_filename
                        if local_file.exists():
                            import shutil
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(local_file), str(output_path))
                        else:
                            return {
                                "success": False,
                                "error": (
                                    f"PPTX generated at {pptx_server_path} "
                                    f"but could not retrieve the file. "
                                    f"Check engine data directory."
                                )
                            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": (
                    "Generation timeout (1 hour). "
                    "Try fewer slides or a simpler prompt."
                )
            }
        except Exception as e:
            logger.error(f"COSMO tool error: {e}")
            return {"success": False, "error": str(e)}

        if not output_path.exists():
            return {
                "success": False,
                "error": "PPTX file was not saved locally"
            }

        file_size_kb = output_path.stat().st_size // 1024

        # --- Visual QA (non-blocking, best-effort) ---
        vision_report = ""
        try:
            from backend.agent.vision_feedback import VisionFeedbackLoop
            from backend.models.model_router import ModelRouter
            vfl = VisionFeedbackLoop(router=ModelRouter())
            pres_id = result.get("id", pptx_filename.replace(".pptx", ""))
            qa = await vfl.analyze_pptx_slides(
                presentation_id=pres_id,
                slide_count=n_slides,
            )
            if qa.get("total_problems", 0) > 0:
                vision_report = (
                    f"\n\n🔍 Visual QA ({qa['slides_analyzed']} slides):\n"
                    f"  Score: {qa['avg_quality']}/10 | "
                    f"Problems: {qa['total_problems']}\n"
                    f"  {qa.get('summary', '')[:300]}"
                )
            else:
                vision_report = "\n\n✅ Visual QA: All slides passed."
        except Exception as e:
            logger.debug(f"Vision QA skipped: {e}")

        return {
            "success": True,
            "output": (
                f"✅ COSMO Presentation готова!\n\n"
                f"📊 Тема: {content[:60]}\n"
                f"📄 Слайдов: {n_slides}\n"
                f"📁 Файл: {output_path.name} ({file_size_kb} KB)\n"
                f"📥 Путь: {output_path}\n\n"
                f"Файл сохранён и готов к скачиванию."
                f"{vision_report}"
            ),
            "file_path": str(output_path),
            "filename": output_path.name,
            "file_size_kb": file_size_kb,
        }

    async def _ping(self, engine_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                r = await c.get(f"{engine_url}/health")
                return r.status_code == 200
        except Exception:
            return False
