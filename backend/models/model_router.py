import logging
from typing import List, Dict, Any, Optional
from backend.models.groq_client import GroqClient, RateLimitExceeded as GroqRateLimit
from backend.models.gemini_client import GeminiClient, RateLimitExceeded as GeminiRateLimit
from backend.models.ollama_client import OllamaClient
from backend.models.anthropic_client import AnthropicClient
from backend.models.retry_wrapper import with_retry, RetryConfig

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
        
        try:
            from backend.config import settings
            self.groq = GroqClient() if settings.GROQ_API_KEY else None
        except Exception:
            self.groq = None
            
        try:
            from backend.config import settings
            self.gemini = GeminiClient() if settings.GOOGLE_API_KEY else None
        except Exception:
            self.gemini = None
            
        try:
            from backend.config import settings
            self.anthropic = AnthropicClient() if getattr(settings, "ANTHROPIC_API_KEY", None) else None
        except Exception:
            self.anthropic = None

    def _get_order(
        self,
        task_hint: str,
        tools: list
    ) -> list:
        """
        Single source of truth for model routing order.
        Ollama-first for local/private/default tasks.
        Cloud providers as fallback when available.
        """
        if task_hint in ("local", "private", "execute"):
            # Privacy/offline: Ollama always first
            order = [self.ollama, self.groq, self.gemini, self.anthropic]
        elif task_hint in self.QUALITY_TASKS:
            # Quality tasks: best model first, Ollama as fallback
            order = [self.anthropic, self.gemini, self.ollama, self.groq]
        elif task_hint in self.SPEED_TASKS:
            # Speed tasks: fastest first
            order = [self.groq, self.ollama, self.gemini, self.anthropic]
        elif tools:
            # Tool calling: Ollama first (it handles tools via injection)
            order = [self.ollama, self.anthropic, self.groq, self.gemini]
        else:
            # Default: Ollama first as primary local provider
            order = [self.ollama, self.groq, self.gemini, self.anthropic]
        return [c for c in order if c is not None]

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default") -> Dict[str, Any]:
        order = self._get_order(task_hint, tools or [])

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
        order = self._get_order(task_hint, tools or [])

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
