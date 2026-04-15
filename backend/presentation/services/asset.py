import os
import httpx
import logging
import urllib.parse
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AssetService:
    """
    Resolves asset queries into image URLs.
    Supports Unsplash API if UNSPLASH_ACCESS_KEY is set.
    Falls back to placehold.co or gradient placeholders if API fails/missing.
    Includes simple in-memory session caching.
    """

    def __init__(self):
        self.api_key = os.environ.get("UNSPLASH_ACCESS_KEY")
        self._cache: Dict[str, str] = {}

    async def get_assets(self, query: Optional[str]) -> Dict[str, str]:
        """
        Returns a dictionary of resolved assets based on the query.
        Currently returns {'background': url} if query is provided.
        """
        if not query or query.strip() == "":
            return {}

        query = query.strip()
        
        # Check cache early
        if query in self._cache:
            return {"background": self._cache[query]}

        image_url = None

        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        "https://api.unsplash.com/search/photos",
                        params={
                            "query": query,
                            "orientation": "landscape",
                            "per_page": 1,
                        },
                        headers={"Authorization": f"Client-ID {self.api_key}"}
                    )
                    response.raise_for_status()
                    data = response.json()
                    if data.get("results") and len(data["results"]) > 0:
                        image_url = data["results"][0]["urls"]["regular"]
                    else:
                        logger.warning(f"No Unsplash results for query: '{query}'")
            except Exception as e:
                logger.error(f"Unsplash API error for query '{query}': {e}")
                image_url = None

        # Fallback to absolute URL placeholder if no image_url found
        if not image_url:
            encoded_query = urllib.parse.quote_plus(query)
            # Using placehold.co to avoid blank images. Dark overlay style.
            image_url = f"https://placehold.co/1920x1080/233554/ccd6f6.png?text={encoded_query}"

        # Cache result
        self._cache[query] = image_url
        return {"background": image_url}

asset_service = AssetService()
