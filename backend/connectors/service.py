"""
ConnectorService: bridge between Nango OAuth tokens
and Composio AI tools. When a user connects GitHub,
Archimedes can immediately start using it.
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

from backend.config import settings
NANGO_BASE = settings.NANGO_BASE_URL
NANGO_SECRET = settings.NANGO_SECRET_KEY


class NangoClient:
    """Thin wrapper around Nango REST API."""

    def __init__(self):
        self.base = NANGO_BASE
        self.headers = {
            "Authorization": f"Bearer {NANGO_SECRET}",
            "Content-Type": "application/json"
        }

    async def get_connection(
        self, integration: str, connection_id: str
    ) -> Optional[Dict]:
        """Get connection with live token from Nango."""
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{self.base}/connection/{connection_id}",
                params={"provider_config_key": integration},
                headers=self.headers
            )
            if r.status_code == 200:
                return r.json()
        return None

    async def list_connections(self, user_id: str) -> List[Dict]:
        """List all active connections for a user."""
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{self.base}/connection",
                params={"connectionId": user_id},
                headers=self.headers
            )
            if r.status_code == 200:
                return r.json().get("connections", [])
        return []

    async def delete_connection(
        self, integration: str, connection_id: str
    ) -> bool:
        """Disconnect a service."""
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.delete(
                f"{self.base}/connection/{connection_id}",
                params={"provider_config_key": integration},
                headers=self.headers
            )
            return r.status_code == 204

    async def get_token(
        self, integration: str, connection_id: str
    ) -> Optional[str]:
        """Get fresh access token — Nango auto-refreshes if expired."""
        conn = await self.get_connection(integration, connection_id)
        if not conn:
            return None
        creds = conn.get("credentials", {})
        return creds.get("access_token") or creds.get("api_key")

    async def make_proxy_request(
        self,
        integration: str,
        connection_id: str,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None
    ) -> Dict:
        """
        Use Nango's proxy to make authenticated API calls.
        Nango auto-injects the token — you never touch tokens directly.
        """
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.request(
                method=method,
                url=f"{self.base}/proxy/{endpoint}",
                headers={
                    **self.headers,
                    "Provider-Config-Key": integration,
                    "Connection-Id": connection_id,
                },
                json=data,
                params=params
            )
            if r.status_code in (200, 201):
                return {"success": True, "data": r.json()}
            return {
                "success": False,
                "error": f"HTTP {r.status_code}: {r.text[:300]}"
            }


# Singleton
nango = NangoClient()
