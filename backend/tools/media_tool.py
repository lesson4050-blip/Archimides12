"""
Archimedes Rich Media Tool (Sprint 3.3).

Standardized media generation and management:
- Image generation via external APIs (Pollinations, DALL·E)
- Diagram generation via Mermaid CLI
- Auto-save to artifacts/ directory with metadata
- Returns file paths + preview URLs for frontend display
"""
import os
import httpx
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = os.path.join("data", "artifacts")


def _ensure_artifacts():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


class MediaTool:
    """Rich media generation tool for images, diagrams, and charts."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "media",
                "description": (
                    "Generate visual media: images from text prompts, "
                    "Mermaid diagrams, or download images from URLs. "
                    "Returns the saved file path."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "generate_image",   # AI image from text prompt
                                "generate_diagram",  # Mermaid diagram from code
                                "download_image",    # Download image from URL
                                "list_artifacts",    # List saved media files
                            ],
                            "description": "Media action to perform"
                        },
                        "prompt": {
                            "type": "string",
                            "description": (
                                "For generate_image: text prompt describing the image. "
                                "For generate_diagram: Mermaid diagram code."
                            )
                        },
                        "url": {
                            "type": "string",
                            "description": "URL for download_image action"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Optional custom filename for the saved file"
                        },
                        "width": {
                            "type": "integer",
                            "description": "Image width in pixels (default 1024)"
                        },
                        "height": {
                            "type": "integer",
                            "description": "Image height in pixels (default 1024)"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["photorealistic", "illustration", "3d", "pixel", "watercolor"],
                            "description": "Image generation style (default: photorealistic)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        action: str = "",
        prompt: str = "",
        url: str = "",
        filename: str = "",
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic",
        **kwargs
    ) -> Dict[str, Any]:
        _ensure_artifacts()

        if action == "generate_image":
            return await self._generate_image(prompt, filename, width, height, style)
        elif action == "generate_diagram":
            return await self._generate_diagram(prompt, filename)
        elif action == "download_image":
            return await self._download_image(url, filename)
        elif action == "list_artifacts":
            return self._list_artifacts()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def _generate_image(
        self,
        prompt: str,
        filename: str = "",
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Dict[str, Any]:
        """Generate an image using Pollinations.ai (free, no API key)."""
        if not prompt:
            return {"success": False, "error": "prompt is required for image generation"}

        try:
            # Enhance prompt with style
            full_prompt = f"{prompt}, {style} style, high quality, detailed"

            # Pollinations.ai — free text-to-image API
            encoded_prompt = httpx.URL(
                f"https://image.pollinations.ai/prompt/"
                f"{full_prompt}?width={width}&height={height}&nologo=true"
            )

            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(str(encoded_prompt))
                response.raise_for_status()

                # Generate filename
                if not filename:
                    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"img_{prompt_hash}_{timestamp}.png"

                filepath = os.path.join(ARTIFACTS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)

                size_kb = len(response.content) / 1024

                # Save metadata
                self._save_metadata(filename, {
                    "type": "generated_image",
                    "prompt": prompt,
                    "style": style,
                    "dimensions": f"{width}x{height}",
                    "size_kb": round(size_kb, 1),
                    "engine": "pollinations.ai",
                })

                return {
                    "success": True,
                    "path": filepath,
                    "filename": filename,
                    "size_kb": round(size_kb, 1),
                    "message": f"Image generated and saved to {filepath}"
                }

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_diagram(
        self, mermaid_code: str, filename: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a diagram from Mermaid code.
        Uses Mermaid.ink API for rendering (no local install needed).
        """
        if not mermaid_code:
            return {"success": False, "error": "prompt (mermaid code) is required"}

        try:
            import base64

            # Encode mermaid code for the API
            encoded = base64.urlsafe_b64encode(
                mermaid_code.encode("utf-8")
            ).decode("ascii")

            diagram_url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=white"

            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(diagram_url)
                response.raise_for_status()

                if not filename:
                    code_hash = hashlib.sha256(mermaid_code.encode()).hexdigest()[:8]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"diagram_{code_hash}_{timestamp}.png"

                filepath = os.path.join(ARTIFACTS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)

                size_kb = len(response.content) / 1024

                self._save_metadata(filename, {
                    "type": "diagram",
                    "mermaid_code": mermaid_code[:200],
                    "size_kb": round(size_kb, 1),
                    "engine": "mermaid.ink",
                })

                return {
                    "success": True,
                    "path": filepath,
                    "filename": filename,
                    "size_kb": round(size_kb, 1),
                    "mermaid_code": mermaid_code,
                    "message": f"Diagram generated and saved to {filepath}"
                }

        except Exception as e:
            logger.error(f"Diagram generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _download_image(
        self, url: str, filename: str = ""
    ) -> Dict[str, Any]:
        """Download an image from a URL and save to artifacts."""
        if not url:
            return {"success": False, "error": "url is required"}

        try:
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Determine extension from content type
                content_type = response.headers.get("content-type", "")
                ext = ".png"
                if "jpeg" in content_type or "jpg" in content_type:
                    ext = ".jpg"
                elif "gif" in content_type:
                    ext = ".gif"
                elif "webp" in content_type:
                    ext = ".webp"
                elif "svg" in content_type:
                    ext = ".svg"

                if not filename:
                    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"download_{url_hash}_{timestamp}{ext}"

                filepath = os.path.join(ARTIFACTS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)

                size_kb = len(response.content) / 1024

                self._save_metadata(filename, {
                    "type": "downloaded_image",
                    "source_url": url,
                    "size_kb": round(size_kb, 1),
                })

                return {
                    "success": True,
                    "path": filepath,
                    "filename": filename,
                    "size_kb": round(size_kb, 1),
                    "message": f"Image downloaded and saved to {filepath}"
                }

        except Exception as e:
            logger.error(f"Image download failed: {e}")
            return {"success": False, "error": str(e)}

    def _list_artifacts(self) -> Dict[str, Any]:
        """List all media artifacts with metadata."""
        _ensure_artifacts()
        items = []

        try:
            for filename in sorted(os.listdir(ARTIFACTS_DIR), reverse=True):
                if filename.endswith(".meta.json"):
                    continue
                filepath = os.path.join(ARTIFACTS_DIR, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    meta = self._load_metadata(filename)
                    items.append({
                        "filename": filename,
                        "path": filepath,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "created": datetime.fromtimestamp(
                            stat.st_ctime
                        ).isoformat(),
                        **(meta or {}),
                    })
        except FileNotFoundError:
            pass

        return {
            "success": True,
            "artifacts": items[:50],
            "count": len(items),
        }

    def _save_metadata(self, filename: str, meta: dict):
        """Save metadata JSON alongside the media file."""
        import json
        meta_path = os.path.join(
            ARTIFACTS_DIR, f"{filename}.meta.json"
        )
        meta["saved_at"] = datetime.now(datetime.timezone.utc).isoformat()
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except (IOError, ValueError, FileNotFoundError) as e:
            logging.getLogger(__name__).warning(f"Media processing error: {e}")

    def _load_metadata(self, filename: str) -> Optional[dict]:
        """Load metadata for a media file."""
        import json
        meta_path = os.path.join(
            ARTIFACTS_DIR, f"{filename}.meta.json"
        )
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
