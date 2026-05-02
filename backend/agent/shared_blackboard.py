import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Global in-memory store for shared state when Redis is unavailable
_shared_local_store: Dict[str, Any] = {}

class SharedBlackboard:
    """
    A single source of truth for multi-agent workflows.
    Prevents context drift across complex, multi-step subtasks by providing
    a shared key-value store that can optionally be backed by Redis for multi-node setups.
    """
    def __init__(self, redis_url: Optional[str] = None, namespace: str = "archimedes:blackboard"):
        self.namespace = namespace
        self.redis_client = None
        
        # Use Redis if URL provided, otherwise fallback to global shared dict
        if redis_url:
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info(f"SharedBlackboard connected to Redis at {redis_url}")
            except ImportError:
                logger.warning("Redis backend requested but redis-py is not installed. Using local shared store.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using local shared store.")

    @property
    def _local_store(self) -> Dict[str, Any]:
        return _shared_local_store

    def _make_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        if self.redis_client:
            try:
                val = await self.redis_client.get(self._make_key(key))
                if val is not None:
                    return json.loads(val)
                return default
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return self._local_store.get(key, default)
        return self._local_store.get(key, default)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Sets a value in the blackboard."""
        self._local_store[key] = value
        if self.redis_client:
            try:
                val_str = json.dumps(value)
                if ttl_seconds:
                    await self.redis_client.setex(self._make_key(key), ttl_seconds, val_str)
                else:
                    await self.redis_client.set(self._make_key(key), val_str)
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False
        return True

    async def append_list(self, key: str, value: Any) -> bool:
        """Appends a value to a list stored at key. Useful for collecting logs/results."""
        current = await self.get(key, [])
        if not isinstance(current, list):
            current = [current]
        current.append(value)
        return await self.set(key, current)

    async def get_all(self) -> Dict[str, Any]:
        """Fetch entire blackboard state."""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"{self.namespace}:*")
                result = {}
                for k in keys:
                    val = await self.redis_client.get(k)
                    local_key = k[len(self.namespace)+1:]
                    result[local_key] = json.loads(val) if val else None
                return result
            except Exception as e:
                logger.error(f"Redis get_all error: {e}")
        return self._local_store.copy()

    async def clear(self) -> bool:
        """Clears the blackboard."""
        self._local_store.clear()
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"{self.namespace}:*")
                if keys:
                    await self.redis_client.delete(*keys)
                return True
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
                return False
        return True
