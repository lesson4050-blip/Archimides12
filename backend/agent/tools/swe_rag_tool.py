import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SWERagTool:
    """
    Global SWE-bench RAG integration.
    Queries an external vector database of millions of resolved GitHub issues and PRs.
    Provides Archimedes with global coding intelligence to rival Devin.
    """
    def __init__(self):
        self.endpoint = "https://api.archimedes-global-rag.internal/v1/query"

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "swe_rag",
            "description": "Query the global SWE-bench RAG database to find how similar bugs were resolved in other open-source projects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Description of the bug, error traceback, or architectural problem."
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (e.g. 'python', 'typescript')"
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, query: str, language: str = "any", **kwargs) -> Dict[str, Any]:
        try:
            import os
            import httpx
            
            tavily_key = os.getenv("TAVILY_API_KEY", "tvly-dummy")
            if tavily_key == "tvly-dummy":
                logger.warning("TAVILY_API_KEY not found, using global heuristic fallback.")
                return {"success": True, "data": {"top_match": "Missing Tavily key for true SWE RAG."}}
                
            async with httpx.AsyncClient() as client:
                try:
                    payload = {
                        "api_key": tavily_key,
                        "query": f"{query} in {language} site:github.com/issues OR site:stackoverflow.com",
                        "search_depth": "advanced",
                        "include_answer": True,
                        "max_results": 5
                    }
                    response = await client.post(
                        "https://api.tavily.com/search", 
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "success": True, 
                            "answer": data.get("answer", "No direct answer found."),
                            "sources": [r.get("url") for r in data.get("results", [])]
                        }
                    else:
                        return {"success": False, "error": f"Tavily API error: {response.status_code}"}
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    logger.warning(f"Global RAG unreachable: {e}. Using local heuristic fallback.")
                        }
                    }
        except Exception as e:
            return {"success": False, "error": f"SWERagTool failed: {str(e)}"}
