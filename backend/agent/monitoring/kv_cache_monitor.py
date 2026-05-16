"""
KV-Cache Hit Rate Monitor.

Tracks whether the system prompt prefix is stable across requests.
A changing prefix = cache miss = wasted money and latency.

Per Manus: KV-cache hit rate is the single most important
production metric for an agent system.
"""
import hashlib
import time
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class KVCacheMonitor:
    """
    Tracks system prompt prefix stability.
    If prefix changes between requests = cache miss.
    """
    
    def __init__(self, window_size: int = 100):
        self._prefix_hashes = deque(maxlen=window_size)
        self._hits = 0
        self._misses = 0
        self._last_prefix_hash: Optional[str] = None
        self._request_count = 0
    
    def record_request(self, system_prompt: str, context_prefix: str = "") -> bool:
        """
        Record a new LLM request.
        Returns True if prefix matches previous (cache HIT).
        Returns False if prefix changed (cache MISS).
        
        The stable prefix is: system_prompt only.
        Variable parts (memory, user context) should NOT be in system_prompt.
        """
        self._request_count += 1
        
        # Only hash the stable part (system prompt)
        stable_part = system_prompt
        prefix_hash = hashlib.md5(stable_part.encode()).hexdigest()[:8]
        
        self._prefix_hashes.append(prefix_hash)
        
        if self._last_prefix_hash is None:
            self._last_prefix_hash = prefix_hash
            return True  # First request = no comparison
        
        is_hit = (prefix_hash == self._last_prefix_hash)
        
        if is_hit:
            self._hits += 1
        else:
            self._misses += 1
            logger.warning(
                f"KV-Cache MISS: prefix changed "
                f"({self._last_prefix_hash} → {prefix_hash}). "
                f"Check system prompt for dynamic content."
            )
        
        self._last_prefix_hash = prefix_hash
        return is_hit
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 1.0
        return round(self._hits / total, 3)
    
    def get_stats(self) -> dict:
        return {
            "hit_rate": self.hit_rate,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": self._request_count,
            "status": (
                "excellent" if self.hit_rate >= 0.9
                else "good" if self.hit_rate >= 0.7
                else "poor — check for dynamic system prompts"
            )
        }
    
    def reset(self):
        self._hits = 0
        self._misses = 0
        self._request_count = 0
        self._last_prefix_hash = None


# Global singleton
kv_cache_monitor = KVCacheMonitor()
