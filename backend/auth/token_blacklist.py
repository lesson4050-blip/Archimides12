"""
JWT Token Revocation List.
Uses Redis (with memory fallback) to invalidate tokens on logout.
Without this, logout only clears cookies — stolen tokens remain valid.
"""
import hashlib
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_MEMORY_BLACKLIST: dict = {}  # {token_hash: expires_at}


class TokenBlacklist:
    """Redis-backed token revocation with in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._initialized = False

    async def _get_redis(self):
        if self._initialized:
            return self._redis
        self._initialized = True
        try:
            from backend.config import settings
            if settings.REDIS_URL:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
                await self._redis.ping()
                logger.info("TokenBlacklist: connected to Redis")
        except Exception as e:
            logger.warning(f"TokenBlacklist: Redis unavailable ({e}), using memory")
            self._redis = None
        return self._redis

    def _token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    async def revoke(self, token: str, expires_at: int) -> None:
        """Add token to blacklist until its natural expiry."""
        ttl = max(expires_at - int(time.time()), 0)
        if ttl <= 0:
            return  # Already expired, no need to blacklist

        key = self._token_hash(token)
        redis = await self._get_redis()

        if redis:
            try:
                await redis.setex(f"blacklist:{key}", ttl, "1")
                return
            except Exception as e:
                logger.warning(f"Redis revoke failed: {e}")

        # Memory fallback
        _MEMORY_BLACKLIST[key] = int(time.time()) + ttl
        # Cleanup expired entries
        now = int(time.time())
        expired = [k for k, v in list(_MEMORY_BLACKLIST.items()) if v < now]
        for k in expired:
            del _MEMORY_BLACKLIST[k]

    async def is_revoked(self, token: str) -> bool:
        """Check if token has been revoked."""
        key = self._token_hash(token)
        redis = await self._get_redis()

        if redis:
            try:
                result = await redis.exists(f"blacklist:{key}")
                return bool(result)
            except Exception as e:
                logger.warning(f"Redis check failed: {e}")

        # Memory fallback
        exp = _MEMORY_BLACKLIST.get(key)
        if exp:
            if int(time.time()) < exp:
                return True
            del _MEMORY_BLACKLIST[key]
        return False


blacklist = TokenBlacklist()
