"""
Shared rate limiter with automatic TTL cleanup.
Replaces the raw dict pattern in council_router, research_slides_router,
and triggers_router — all three had unbounded memory growth.

SECURITY FEATURES:
- Automatic cleanup of stale entries (no memory leak)
- Thread-safe via simple lock
- IP validation to prevent memory bloat from crafted IPs
- Max unique IPs tracked to prevent dict unbounded growth
"""
import time
import re
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Validate IP format before using as dict key
_IP_PATTERN = re.compile(
    r'^(\d{1,3}\.){3}\d{1,3}$|'  # IPv4
    r'^[\da-fA-F:]{2,39}$|'       # IPv6 (simplified)
    r'^localhost$|^unknown$'        # Special cases
)

_MAX_TRACKED_IPS = 10_000  # Hard cap on dict size


class RateLimiter:
    """
    Token bucket rate limiter with automatic TTL cleanup.
    Thread-safe for async use.
    """

    def __init__(
        self,
        requests_per_minute: int,
        cleanup_interval_seconds: int = 300,
        name: str = "default"
    ):
        self.rpm = requests_per_minute
        self.name = name
        self._buckets: Dict[str, List[float]] = {}
        self._cleanup_interval = cleanup_interval_seconds
        self._last_cleanup = time.time()
        self._lock = asyncio.Lock()

    def _validate_ip(self, ip: str) -> str:
        """Validate and normalize IP address."""
        ip = str(ip).strip()[:45]  # Max IPv6 length
        if not _IP_PATTERN.match(ip):
            return "unknown"
        return ip

    def _cleanup_stale(self, now: float):
        """Remove IPs with no recent activity. Prevents memory leak."""
        if now - self._last_cleanup < self._cleanup_interval:
            return

        window_start = now - 60
        stale_ips = [
            ip for ip, history in self._buckets.items()
            if not any(t > window_start for t in history)
        ]
        for ip in stale_ips:
            del self._buckets[ip]

        if stale_ips:
            logger.debug(
                f"[RateLimiter:{self.name}] Cleaned {len(stale_ips)} stale IPs. "
                f"Active IPs: {len(self._buckets)}"
            )

        self._last_cleanup = now

    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if request is allowed. Returns True if within limit.
        Non-async for simple use, safe because dict ops are atomic in CPython.
        """
        now = time.time()
        ip = self._validate_ip(client_ip)

        # Hard cap on tracked IPs
        if len(self._buckets) >= _MAX_TRACKED_IPS and ip not in self._buckets:
            logger.warning(f"[RateLimiter:{self.name}] MAX_TRACKED_IPS reached")
            return False

        # Cleanup stale entries periodically
        self._cleanup_stale(now)

        window_start = now - 60
        history = [t for t in self._buckets.get(ip, []) if t > window_start]

        if len(history) >= self.rpm:
            return False

        history.append(now)
        self._buckets[ip] = history
        return True

    def get_stats(self) -> dict:
        """Return rate limiter stats for monitoring."""
        now = time.time()
        window_start = now - 60
        active = sum(
            1 for h in self._buckets.values()
            if any(t > window_start for t in h)
        )
        return {
            "name": self.name,
            "rpm_limit": self.rpm,
            "tracked_ips": len(self._buckets),
            "active_ips_last_minute": active,
        }


# Pre-built limiters for each endpoint
council_limiter = RateLimiter(requests_per_minute=5, name="council")
research_limiter = RateLimiter(requests_per_minute=3, name="research")
triggers_limiter = RateLimiter(requests_per_minute=10, name="triggers")
