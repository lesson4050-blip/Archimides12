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
                            "enum": ["basic", "advanced", "neural"],
                            "description": "basic=faster, advanced=more results, neural=Tavily+Exa"
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

        if search_depth == "neural":
            import asyncio
            tavily_task = asyncio.create_task(self._search_tavily(query, "advanced", max_results))
            exa_task = asyncio.create_task(self._search_exa(query, max_results))
            
            tavily_res, exa_res = await asyncio.gather(tavily_task, exa_task)
            
            output_parts = []
            if tavily_res.get("success"):
                output_parts.append("--- TAVILY (QUICK FACTS) ---\n" + tavily_res.get("output", ""))
            if exa_res.get("success"):
                output_parts.append("--- EXA (DEEP PARSING) ---\n" + exa_res.get("output", ""))
                
            if not output_parts:
                return {"success": False, "error": "Both Tavily and Exa failed in Neural search."}
                
            return {
                "success": True,
                "output": "\n\n".join(output_parts),
                "note": "Neural Research Engine completed (Tavily + Exa)"
            }

        # Try Tavily first (best quality)
        if settings.TAVILY_API_KEY:
            result = await self._search_tavily(query, search_depth, max_results)
            if result.get("success"):
                return result
            logger.warning(f"Tavily failed: {result.get('error')}. Trying Brave...")

        # Fallback 1: Brave Search (high quality, free tier available)
        brave_key = getattr(settings, 'BRAVE_API_KEY', '')
        if brave_key:
            result = await self._search_brave(query, max_results, brave_key)
            if result.get("success"):
                result["note"] = "Results from Brave Search"
                return result
            logger.warning(f"Brave failed: {result.get('error')}. Trying DuckDuckGo...")

        # Fallback 2: DuckDuckGo (free, no API key, lowest quality)
        result = await self._search_duckduckgo(query, max_results)
        if result.get("success"):
            result["note"] = "Results from DuckDuckGo (set TAVILY_API_KEY or BRAVE_API_KEY for better results)"
            return result

        return {"success": False, "error": "All search engines failed (Tavily, Brave, DuckDuckGo)"}

    async def _read_top_pages(
        self, results: list, query: str
    ) -> str:
        """Read actual page content for top search results."""
        from backend.tools.web_tool import WebTool
        web = WebTool()
        full_content = []
        for r in results[:2]:
            url = r.get("url", "")
            if not url or "reddit.com" in url:
                continue
            try:
                page_result = await web.execute(
                    url=url, query=query
                )
                if page_result.get("success"):
                    content = page_result.get("content", "")
                    if len(content) > 200:
                        full_content.append(
                            f"[From {url}]:\n{content[:1500]}"
                        )
            except (TimeoutError, IOError, ValueError) as e:
                logging.getLogger(__name__).warning(f"Search tool request failed: {e}")
        return "\n\n".join(full_content)

    async def _multi_hop_search(self, initial_query: str, max_hops: int = 3) -> str:
        all_results = []
        current_query = initial_query
        knowledge = []
        
        from backend.models.model_router import ModelRouter
        router = ModelRouter()
        
        for hop in range(max_hops):
            # Execute single search
            res = None
            if settings.TAVILY_API_KEY:
                res = await self._search_tavily(current_query, "basic", 5)
            if not res or not res.get("success"):
                res = await self._search_duckduckgo(current_query, 5)

            hop_text = res.get("output", "") if res else ""
            
            # Read actual pages for richer content
            page_content = await self._read_top_pages(
                res.get("results", []) if res else [], current_query
            )
            if page_content:
                hop_text = hop_text + "\n\nFULL PAGE CONTENT:\n" + page_content

            knowledge.append(f"Hop {hop+1}:\n{hop_text}")
            all_results.append(f"--- Search [{hop+1}/{max_hops}] '{current_query}' ---\n{hop_text}")
            
            # Ask LLM if we have enough info
            analysis_prompt = f"""
Goal: {initial_query}
Found so far: { hop_text[:2000] }
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
        
        # Synthesize with citation instruction
        synthesis_prompt = (
            f"Question: {initial_query}\n\n"
            f"Research:\n" + "\n\n".join(knowledge[:3])
            + "\n\nWrite a comprehensive, accurate answer. "
            f"Cite sources as [1], [2] inline. "
            f"Add 'Sources:' section at the end with URLs. "
            f"Be specific with numbers, dates, names."
        )
        
        try:
            synth_resp = await router.generate(
                messages=[{"role": "user", "content": synthesis_prompt}],
                task_hint="think"
            )
            synthesized = synth_resp.get("text", "")
            if synthesized and len(synthesized) > 100:
                return synthesized
        except (TimeoutError, IOError, ValueError) as e:
            logging.getLogger(__name__).warning(f"Search tool request failed: {e}")

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

                formatted_output = self._format_search_results(results, max_results, query)
                if answer:
                    formatted_output = f"DIRECT ANSWER: {answer}\n\n" + formatted_output

                return {
                    "success": True,
                    "output": formatted_output,
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

                # Instant answer
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "content": data["AbstractText"]
                    })

                # Related topics
                for topic in data.get("RelatedTopics", []):
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:60],
                            "url": topic.get("FirstURL", ""),
                            "content": topic.get("Text", "")
                        })

                if not results:
                    return {
                        "success": False,
                        "error": "DuckDuckGo returned no results"
                    }

                formatted_output = self._format_search_results(results, max_results, query)
                return {
                    "success": True,
                    "output": formatted_output,
                    "results": results,
                    "source": "duckduckgo"
                }

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return {"success": False, "error": str(e)}

    async def _search_brave(
        self, query: str, max_results: int, api_key: str
    ) -> Dict[str, Any]:
        """Brave Search API — high quality, free tier (1 req/sec, 2000/month)."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                    params={"q": query, "count": min(max_results, 20)},
                )
                response.raise_for_status()
                data = response.json()

                results = []

                for r in data.get("web", {}).get("results", [])[:max_results]:
                    title = r.get("title", "No title")
                    url = r.get("url", "")
                    desc = r.get("description", "")[:400]
                    results.append({"title": title, "url": url, "content": desc})

                if not results:
                    return {"success": False, "error": "Brave returned no results"}

                formatted_output = self._format_search_results(results, max_results, query)
                return {
                    "success": True,
                    "output": formatted_output,
                    "results": results,
                    "source": "brave",
                }
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return {"success": False, "error": str(e)}

    async def _search_exa(
        self, query: str, max_results: int
    ) -> Dict[str, Any]:
        """
        Deep document parsing via Exa API.
        """
        if not settings.EXA_API_KEY:
            return {"success": False, "error": "EXA_API_KEY is missing from config."}
            
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": settings.EXA_API_KEY},
                    json={
                        "query": query,
                        "numResults": max_results,
                        "contents": {"text": True}
                    }
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                
                # Map 'text' to 'content' for the unified formatter
                for r in results:
                    r["content"] = r.get("text", "")
                    
                formatted_output = self._format_search_results(results, max_results, query)
                return {
                    "success": True,
                    "output": formatted_output,
                    "results": results,
                    "source": "exa"
                }
        except Exception as e:
            logger.error(f"Exa search error: {e}")
            return {"success": False, "error": str(e)}

    def _get_domain_label(self, url: str) -> str:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
                
            state_ru = {
                "ria.ru", "tass.ru", "rt.com", "sputniknews.com", "rg.ru", "iz.ru", 
                "lenta.ru", "ukraina.ru", "gazeta.ru", "kp.ru", "tsargrad.tv", 
                "vz.ru", "ntv.ru", "1tv.ru", "smotrim.ru", "vesti.ru", "tass.com"
            }
            independent_ru = {
                "meduza.io", "novayagazeta.eu", "tvrain.tv", "thebell.io", "vpost.media"
            }
            business_ru = {
                "rbc.ru", "kommersant.ru", "vedomosti.ru"
            }
            ua_media = {
                "unian.net", "unian.ua", "pravda.com.ua", "liga.net", "censor.net", 
                "nv.ua", "tsn.ua", "obozrevatel.com", "ukrinform.net", "ukrinform.ru", 
                "hromadske.ua", "kyivindependent.com", "kyivpost.com", "rbc.ua", 
                "uatv.ua", "suspilne.media"
            }
            intl_news = {
                "reuters.com", "apnews.com", "bloomberg.com", "afp.com", "ft.com", 
                "nytimes.com", "washingtonpost.com", "theguardian.com", "bbc.com", 
                "bbc.co.uk", "dw.com", "euronews.com", "france24.com"
            }
            analytical = {
                "understandingwar.org", "cfr.org", "rand.org", "rusi.org", 
                "chathamhouse.org", "atlanticcouncil.org"
            }
            
            for d in state_ru:
                if domain == d or domain.endswith("." + d):
                    return "Russian State-Controlled Media"
            for d in independent_ru:
                if domain == d or domain.endswith("." + d):
                    return "Russian Independent Media (Exiled)"
            for d in business_ru:
                if domain == d or domain.endswith("." + d):
                    return "Russian Business/Local Media"
            for d in ua_media:
                if domain == d or domain.endswith("." + d):
                    return "Ukrainian Media"
            for d in intl_news:
                if domain == d or domain.endswith("." + d):
                    return "International News / Public Broadcaster"
            for d in analytical:
                if domain == d or domain.endswith("." + d):
                    return "Independent Think Tank / Analysis"
                    
            if domain.endswith(".gov.ua"):
                return "Ukrainian Government/Official Source"
            if domain.endswith(".mil.gov.ua") or domain == "mil.gov.ua":
                return "Ukrainian Military Official Source"
            if domain.endswith(".mil.ru") or domain == "mil.ru":
                return "Russian Ministry of Defense Official Source"
            if domain.endswith(".gov.ru") or domain.endswith(".gov"):
                return "Government Official Source"
                
            if domain.endswith(".ru"):
                return "Russian Domain Source"
            if domain.endswith(".ua"):
                return "Ukrainian Domain Source"
            if domain.endswith(".by"):
                return "Belarusian Domain Source"
                
            return "Web Source"
        except Exception:
            return "Web Source"

    def _format_search_results(self, results: list, max_results: int, query: str = "") -> str:
        # Detect if the query specifically targets video/social platforms
        query_lower = query.lower()
        wants_video = any(w in query_lower for w in ["video", "youtube", "ролик", "видео", "клип", "фильм", "watch"])
        wants_social = any(w in query_lower for w in ["reddit", "twitter", "x.com", "tiktok", "facebook", "instagram"])
        
        from urllib.parse import urlparse
        
        filtered_results = []
        for r in results:
            url = r.get("url") or r.get("link") or ""
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                
                # Check if it matches any excluded domains
                is_excluded = False
                if not wants_video and (domain in {"youtube.com", "youtu.be", "tiktok.com"} or domain.endswith(".youtube.com")):
                    is_excluded = True
                if not wants_social and (domain in {"twitter.com", "x.com", "facebook.com", "instagram.com", "reddit.com", "pinterest.com"}):
                    is_excluded = True
                    
                if is_excluded:
                    continue
            except Exception:
                pass
            
            filtered_results.append(r)
            
        formatted = []
        for i, r in enumerate(filtered_results[:max_results]):
            title = r.get("title") or r.get("name") or "No title"
            url = r.get("url") or r.get("link") or ""
            content = r.get("content") or r.get("snippet") or r.get("text") or ""
            
            label = self._get_domain_label(url)
            
            formatted.append(
                f"[{i+1}] [{label}] {title}\n"
                f"URL: {url}\n"
                f"{content[:400]}"
            )
        return "\n\n".join(formatted)
