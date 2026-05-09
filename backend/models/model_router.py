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
    _gemini_blocked_until: float = 0.0

    def __init__(self):
        self.ollama = OllamaClient()
        self._ollama_healthy = True
        self._last_health_check = 0
        self._health_cache_ttl = 30 # seconds
        self._health_check_lock = None
        
        try:
            self.groq = GroqClient() if settings.GROQ_API_KEY else None
            # Validate key presence (not validity yet)
            if self.groq and not settings.GROQ_API_KEY.startswith("gsk_"):
                 logger.warning("GROQ_API_KEY does not look valid. Disabling Groq.")
                 self.groq = None
        except Exception as e:
            logger.error(f"Groq initialization failed: {e}")
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

        if self._health_check_lock is None:
            self._health_check_lock = asyncio.Lock()

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

    def classify_complexity(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]) -> str:
        """
        Classify task complexity based on intent, context depth, and tool surface.
        Prevents routing complex reasoning/coding tasks to fast models with small contexts.
        """
        # 1. Check for intent keywords in the last user message
        last_user_msg = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        complexity_keywords = {"debug", "fix", "refactor", "implement", "analyze", "audit", "bottleneck", "deadlock"}
        if any(kw in last_user_msg.lower() for kw in complexity_keywords):
            return "complex"

        # 2. Check conversation depth (history > 5 messages usually implies a complex follow-up)
        if len(messages) > 6:
            return "complex"

        # 3. Check tool surface (more than 2 tools suggests coordination needs)
        if tools and len(tools) > 2:
            return "complex"

        # 4. Fallback to text length (but with a stricter threshold for triviality)
        text_length = sum(len(m.get("content", "")) for m in messages if isinstance(m.get("content"), str))
        if text_length > 3000:
            return "complex"

        return "trivial"

    async def _get_order(
        self,
        task_hint: str,
        tools: list,
        complexity: str = "trivial"
    ) -> list:
        """
        Routing order: 
        - Trivial/Speed: Groq -> Gemini -> Ollama -> Anthropic
        - Complex/Quality: Anthropic -> Gemini -> Ollama -> Groq
        - Local/Private: Ollama -> Groq
        """
        ollama_ok = await self._check_ollama_health()
        
        if task_hint in ("local", "private"):
            order = [self.ollama, self.groq]
        elif task_hint in self.QUALITY_TASKS or complexity == "complex":
            order = [self.gemini, self.anthropic, self.groq, self.ollama]
        elif task_hint in self.SPEED_TASKS or complexity == "trivial":
            order = [self.groq, self.gemini, self.ollama, self.anthropic]
        elif tools:
            order = [self.gemini, self.anthropic, self.groq, self.ollama]
        else:
            order = [self.groq, self.gemini, self.anthropic, self.ollama]
        
        available = [c for c in order if c is not None]
        if not ollama_ok and self.ollama in available:
            # Move ollama to the very end if unhealthy
            available.remove(self.ollama)
            available.append(self.ollama)
            
        return available

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default") -> Dict[str, Any]:
        complexity = self.classify_complexity(messages, tools)
        order = await self._get_order(task_hint, tools or [], complexity)

        errors = []
        for client in order:
            import time
            now = time.time()
            if isinstance(client, GeminiClient) and now < ModelRouter._gemini_blocked_until:
                errors.append("Gemini blocked (rate limit cooldown)")
                continue
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
                if isinstance(client, GeminiClient):
                    import time
                    ModelRouter._gemini_blocked_until = time.time() + 3600
                    logger.warning("Gemini rate limited — blocking for 60 minutes")
                logger.warning(f"Model tier {client.__class__.__name__} failed with rate limit. Trying next...")
                errors.append(str(e))
                continue
            except Exception as e:
                logger.error(f"Model tier {client.__class__.__name__} failed with error: {e}")
                errors.append(str(e))
                continue
                
        last_error = errors[-1] if errors else "Unknown error"
        return {
            "text": "",
            "error": f"All model providers failed. Last error: {last_error}",
            "model_used": "none",
            "all_failed": True
        }

    async def generate_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default", on_token=None) -> Dict[str, Any]:
        complexity = self.classify_complexity(messages, tools)
        order = await self._get_order(task_hint, tools or [], complexity)

        errors = []
        for client in order:
            import time
            now = time.time()
            if isinstance(client, GeminiClient) and now < ModelRouter._gemini_blocked_until:
                errors.append("Gemini blocked (rate limit cooldown)")
                continue
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
                if isinstance(client, GeminiClient):
                    import time
                    ModelRouter._gemini_blocked_until = time.time() + 3600
                    logger.warning("Gemini rate limited — blocking for 60 minutes")
                logger.warning(f"Model tier {client.__class__.__name__} failed with rate limit. Trying next...")
                errors.append(str(e))
                continue
            except Exception as e:
                logger.error(f"Model tier {client.__class__.__name__} failed with error: {e}")
                errors.append(str(e))
                continue
                
        last_error = errors[-1] if errors else "Unknown error"
        return {
            "text": "",
            "error": f"All model providers failed. Last error: {last_error}",
            "model_used": "none",
            "all_failed": True
        }

    async def generate_with_image(
        self,
        prompt: str,
        image_base64: str,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """Routes vision requests to a multimodal model (Gemini)."""
        if self.gemini:
            return await self.gemini.generate_with_image(prompt, image_base64, image_mime_type)
        return {"text": "No vision model available", "error": "gemini_not_configured"}

_router_instance: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance
