"""
WebTool: fast HTTP-based page reader for simple pages.
Use browser tool for JS-heavy/interactive pages.
Use this tool for APIs, RSS, plain text URLs, documentation.
"""
import logging
import re
import httpx
from typing import Dict, Any
from html.parser import HTMLParser

logger = logging.getLogger(__name__)
MAX_CHARS = 12000


class _TextExtractor(HTMLParser):
    """Minimal HTML to text extractor."""
    SKIP_TAGS = {"script", "style", "nav", "footer", "head", "noscript"}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


class WebTool:
    """Fast URL content reader without browser overhead."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_read",
                "description": (
                    "Quickly fetch and read the text content of a URL. "
                    "Faster than browser for static pages, APIs, docs, RSS. "
                    "Use browser tool instead for JavaScript-rendered pages."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch"
                        },
                        "query": {
                            "type": "string",
                            "description": "Filter content to sections matching this term"
                        },
                        "raw": {
                            "type": "boolean",
                            "description": "Return raw response (for APIs/JSON endpoints)"
                        }
                    },
                    "required": ["url"]
                }
            }
        }

    async def execute(
        self,
        url: str,
        query: str = "",
        raw: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        if not url:
            return {"success": False, "error": "url is required"}

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/json,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                headers=headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            # JSON response
            if "json" in content_type or raw:
                try:
                    from backend.utils.json_repair import repair_and_parse
                    data, _ = repair_and_parse(response.text)
                    return {
                        "success": True,
                        "url": str(response.url),
                        "content": str(data or response.text)[:MAX_CHARS],
                        "content_type": content_type
                    }
                except Exception:
                    return {
                        "success": True,
                        "url": str(response.url),
                        "content": response.text[:MAX_CHARS]
                    }

            # HTML response — extract text
            parser = _TextExtractor()
            parser.feed(response.text)
            text = parser.get_text()

            # Clean up
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)

            if query:
                lines = text.split("\n")
                relevant = []
                query_lower = query.lower()
                for i, line in enumerate(lines):
                    if any(t in line.lower() for t in query_lower.split()):
                        start = max(0, i - 1)
                        end = min(len(lines), i + 4)
                        relevant.extend(lines[start:end])
                        relevant.append("---")
                if relevant:
                    text = "\n".join(relevant[:150])

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS] + f"\n[...truncated, total {len(text)} chars]"

            return {
                "success": True,
                "url": str(response.url),
                "content": text,
                "chars": len(text)
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {url}",
                "hint": "Try browser tool for pages requiring JavaScript"
            }
        except Exception as e:
            logger.error(f"WebTool error for {url}: {e}")
            return {"success": False, "error": str(e)}
