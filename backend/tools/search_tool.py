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
                        },
                        "multi_hop": {
                            "type": "boolean",
                            "description": "Enable iterative multi-hop search for deep research"
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
        multi_hop: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        if not query:
            return {"success": False, "error": "query is required"}

        if multi_hop:
            result_text = await self._multi_hop_search(query)
            return {
                "success": True, 
                "output": result_text,
                "note": "Multi-hop search completed."
            }

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

    async def _multi_hop_search(self, initial_query: str, max_hops: int = 3) -> str:
        all_results = []
        current_query = initial_query
        
        from backend.models.model_router import ModelRouter
        router = ModelRouter()
        
        for hop in range(max_hops):
            # Execute single search
            res = None
            if settings.TAVILY_API_KEY:
                res = await self._search_tavily(current_query, "basic", 5)
            if not res or not res.get("success"):
                res = await self._search_duckduckgo(current_query, 5)

            text = res.get("output", "") if res else ""
            all_results.append(f"--- Search [{hop+1}/{max_hops}] '{current_query}' ---\n{text}")
            
            # Ask LLM if we have enough info
            analysis_prompt = f"""
Goal: {initial_query}
Found so far: { text[:2000] }
If the goal is fully answered by the findings, output 'DONE'.
If we need more info (e.g. data is missing or incomplete), output a single new search query string.
Do not output any reasoning, just 'DONE' or the new query.
"""
            analysis = await router.generate(
                messages=[{"role": "user", "content": analysis_prompt}],
                task_hint="think"
            )
            ans = analysis.get("text", "").strip()
            if "DONE" in ans.upper() or not ans:
                break
            current_query = ans
            
        return "\n\n".join(all_results)

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
