import asyncio
import time
import httpx
import logging
from typing import List, Dict, Any, Optional
from backend.models.groq_client import GroqClient, RateLimitExceeded as GroqRateLimit
from backend.models.gemini_client import GeminiClient, RateLimitExceeded as GeminiRateLimit
from backend.models.ollama_client import OllamaClient
from backend.models.anthropic_client import AnthropicClient
from backend.models.retry_wrapper import with_retry, RetryConfig
from backend.config import settings

GROQ_RETRY = RetryConfig(max_retries=3, base_delay=2.0, max_delay=30.0)
GEMINI_RETRY = RetryConfig(max_retries=2, base_delay=5.0, max_delay=60.0)
DEFAULT_RETRY = RetryConfig(max_retries=1, base_delay=1.0, max_delay=5.0)

logger = logging.getLogger(__name__)

class AllModelsExhausted(Exception):
    pass

class ModelRouter:
    # Speed-first routing categories
    SPEED_TASKS = {"search", "browse", "realtime", "summarize",
                   "translate", "quick", "simple", "fast"}
    QUALITY_TASKS = {"think", "plan", "execute", "code", "debug"}
    CREATIVE_TASKS = {"image", "creative", "persona"}

    def __init__(self):
        self.ollama = OllamaClient()
        self._ollama_healthy = True
        self._last_health_check = 0
        self._health_cache_ttl = 30 # seconds
        self._health_check_lock = asyncio.Lock()
        
        try:
            self.groq = GroqClient() if settings.GROQ_API_KEY else None
        except Exception:
            self.groq = None
            
        try:
            self.gemini = GeminiClient() if settings.GOOGLE_API_KEY else None
        except Exception:
            self.gemini = None
            
        try:
            self.anthropic = AnthropicClient() if getattr(settings, "ANTHROPIC_API_KEY", None) else None
        except Exception:
            self.anthropic = None

    async def _check_ollama_health(self) -> bool:
        """Checks if Ollama is reachable and caches the result (with lock)."""
        # Quick exit if cache is fresh
        if time.time() - self._last_health_check < self._health_cache_ttl:
            return self._ollama_healthy

        async with self._health_check_lock:
            # Double-check inside the lock
            now = time.time()
            if now - self._last_health_check < self._health_cache_ttl:
                return self._ollama_healthy

            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                    self._ollama_healthy = response.status_code == 200
            except Exception:
                self._ollama_healthy = False
                logger.warning("Ollama health check failed! Falling back to cloud providers.")

            self._last_health_check = now
            return self._ollama_healthy

    async def get_health_status(self) -> Dict[str, Any]:
        """Returns health status of all providers."""
        ollama_ok = await self._check_ollama_health()
        return {
            "ollama": "healthy" if ollama_ok else "unreachable",
            "groq": "available" if self.groq else "no_key",
            "gemini": "available" if self.gemini else "no_key",
            "anthropic": "available" if self.anthropic else "no_key"
        }

    async def _get_order(
        self,
        task_hint: str,
        tools: list
    ) -> list:
        """
        Single source of truth for model routing order.
        If Ollama is down, it is moved to the end of the list.
        """
        ollama_ok = await self._check_ollama_health()
        
        if task_hint in ("local", "private", "execute"):
            order = [self.ollama, self.groq, self.gemini, self.anthropic]
        elif task_hint in self.QUALITY_TASKS:
            order = [self.ollama, self.anthropic, self.gemini, self.groq]
        elif task_hint in self.SPEED_TASKS:
            order = [self.ollama, self.groq, self.gemini, self.anthropic]
        elif tools:
            order = [self.ollama, self.anthropic, self.groq, self.gemini]
        else:
            order = [self.ollama, self.groq, self.gemini, self.anthropic]
        
        available = [c for c in order if c is not None]
        if not ollama_ok and self.ollama in available:
            # Move ollama to the very end if unhealthy
            available.remove(self.ollama)
            available.append(self.ollama)
            
        return available

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default") -> Dict[str, Any]:
        order = await self._get_order(task_hint, tools or [])

        errors = []
        for client in order:
            try:
                config = GROQ_RETRY if isinstance(client, GroqClient) else (GEMINI_RETRY if isinstance(client, GeminiClient) else DEFAULT_RETRY)
                return await with_retry(
                    client.generate_with_tools,
                    messages=messages,
                    tools=tools,
                    task_hint=task_hint,
                    config=config,
                    operation_name=f"{client.__class__.__name__} generate"
                )
            except (GroqRateLimit, GeminiRateLimit) as e:
                logger.warning(f"Model tier {client.__class__.__name__} failed with rate limit. Trying next...")
                errors.append(str(e))
                continue
            except Exception as e:
                logger.error(f"Model tier {client.__class__.__name__} failed with error: {e}")
                errors.append(str(e))
                continue
                
        raise AllModelsExhausted(f"All model tiers failed: {', '.join(errors)}")

    async def generate_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default", on_token=None) -> Dict[str, Any]:
        order = await self._get_order(task_hint, tools or [])

        errors = []
        for client in order:
            try:
                config = GROQ_RETRY if isinstance(client, GroqClient) else (GEMINI_RETRY if isinstance(client, GeminiClient) else DEFAULT_RETRY)
                if hasattr(client, "generate_stream"):
                    return await with_retry(
                        client.generate_stream,
                        messages=messages,
                        tools=tools,
                        on_token=on_token,
                        task_hint=task_hint,
                        config=config,
                        operation_name=f"{client.__class__.__name__} generate_stream"
                    )
                else:
                    return await with_retry(
                        client.generate_with_tools,
                        messages=messages,
                        tools=tools,
                        task_hint=task_hint,
                        config=config,
                        operation_name=f"{client.__class__.__name__} generate"
                    )
            except (GroqRateLimit, GeminiRateLimit) as e:
                logger.warning(f"Model tier {client.__class__.__name__} failed with rate limit. Trying next...")
                errors.append(str(e))
                continue
            except Exception as e:
                logger.error(f"Model tier {client.__class__.__name__} failed with error: {e}")
                errors.append(str(e))
                continue
                
        raise AllModelsExhausted(f"All model tiers failed: {', '.join(errors)}")

_router_instance: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance
