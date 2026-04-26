import logging
from typing import List, Dict, Any, Optional
from backend.models.groq_client import GroqClient, RateLimitExceeded as GroqRateLimit
from backend.models.gemini_client import GeminiClient, RateLimitExceeded as GeminiRateLimit
from backend.models.ollama_client import OllamaClient
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
                   "translate", "quick", "simple"}
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

    def _get_order(
        self,
        task_hint: str,
        tools: list
    ) -> list:
        """Single source of truth for model routing order."""
        if task_hint in self.SPEED_TASKS:
            order = [self.groq, self.gemini, self.ollama]
        elif task_hint in self.QUALITY_TASKS:
            order = [self.ollama, self.groq, self.gemini]
        elif tools:
            order = [self.groq, self.gemini, self.ollama]
        else:
            order = [self.groq, self.gemini, self.ollama]
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
                        config=config,
                        operation_name=f"{client.__class__.__name__} generate_stream"
                    )
                else:
                    return await with_retry(
                        client.generate_with_tools,
                        messages=messages,
                        tools=tools,
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
