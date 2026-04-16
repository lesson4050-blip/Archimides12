import logging
import httpx
from typing import Dict, Any
from backend.config import settings

logger = logging.getLogger(__name__)


class SearchTool:
    """
    Internet search with Tavily (primary) + DuckDuckGo (free fallback).
    Always works even without API keys.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search",
                "description": (
                    "Search the internet for information. "
                    "Returns titles, URLs, and text snippets. "
                    "Use specific queries for best results."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "basic=faster, advanced=more results"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max results to return (default 8)"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def execute(
        self,
        query: str = "",
        search_depth: str = "basic",
        max_results: int = 8,
        **kwargs
    ) -> Dict[str, Any]:
        if not query:
            return {"success": False, "error": "query is required"}

        # Try Tavily first
        if settings.TAVILY_API_KEY:
            result = await self._search_tavily(query, search_depth, max_results)
            if result.get("success"):
                return result
            logger.warning(f"Tavily failed: {result.get('error')}. Trying DuckDuckGo...")

        # Fallback: DuckDuckGo (free, no API key)
        result = await self._search_duckduckgo(query, max_results)
        if result.get("success"):
            result["note"] = "Results from DuckDuckGo (set TAVILY_API_KEY for better results)"
            return result

        return {"success": False, "error": "All search engines failed"}

    async def _search_tavily(
        self, query: str, depth: str, max_results: int
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": depth,
                        "max_results": max_results,
                        "include_answer": True
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                answer = data.get("answer", "")

                formatted = []
                if answer:
                    formatted.append(f"DIRECT ANSWER: {answer}\n")
                
                for i, r in enumerate(results[:max_results]):
                    formatted.append(
                        f"[{i+1}] {r.get('title', 'No title')}\n"
                        f"URL: {r.get('url', '')}\n"
                        f"{r.get('content', '')[:400]}"
                    )

                return {
                    "success": True,
                    "output": "\n\n".join(formatted),
                    "results": results,
                    "source": "tavily"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _search_duckduckgo(
        self, query: str, max_results: int
    ) -> Dict[str, Any]:
        """
        DuckDuckGo Instant Answer API — free, no key required.
        Limited but always available.
        """
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # DuckDuckGo Instant Answer API
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                formatted = []

                # Instant answer
                if data.get("AbstractText"):
                    formatted.append(
                        f"ANSWER: {data['AbstractText']}\n"
                        f"Source: {data.get('AbstractURL', '')}"
                    )
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "content": data["AbstractText"]
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:max_results - 1]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        url = topic.get("FirstURL", "")
                        text = topic.get("Text", "")[:300]
                        formatted.append(f"• {text}\n  {url}")
                        results.append({"title": text[:60], "url": url, "content": text})

                if not formatted:
                    return {
                        "success": False,
                        "error": "DuckDuckGo returned no results"
                    }

                return {
                    "success": True,
                    "output": "\n\n".join(formatted),
                    "results": results,
                    "source": "duckduckgo"
                }

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return {"success": False, "error": str(e)}
