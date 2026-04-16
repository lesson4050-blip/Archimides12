import logging
import httpx
from typing import Dict, Any
from backend.config import settings

logger = logging.getLogger(__name__)

class SearchTool:
    """
    Provides internet search capabilities via Tavily API.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Searches the internet for information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "basic"}
                    },
                    "required": ["query"]
                }
            }
        }
    async def execute(self, query: str = "", search_depth: str = "advanced", **kwargs) -> Dict[str, Any]:
        if not query:
            return {"success": False, "error": "Search query is required."}
        api_key = settings.TAVILY_API_KEY
        if not api_key:
            return {"success": False, "error": "TAVILY_API_KEY not set in environment."}
            
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": 10
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Format response for agent
                results = data.get("results", [])
                formatted = "\n".join([
                    f"[{i+1}] {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}..."
                    for i, r in enumerate(results)
                ])
                
                return {
                    "success": True,
                    "output": formatted,
                    "results": results
                }
        except Exception as e:
            logger.error(f"Search API error: {e}")
            return {"success": False, "error": str(e)}
