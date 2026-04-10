import logging
from typing import List, Dict, Any, Optional
from backend.models.groq_client import GroqClient, RateLimitExceeded as GroqRateLimit
from backend.models.gemini_client import GeminiClient, RateLimitExceeded as GeminiRateLimit
from backend.models.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class AllModelsExhausted(Exception):
    pass

class ModelRouter:
    # Tasks that benefit from Gemma's native reasoning via Ollama
    OLLAMA_FIRST_TASKS = {"think", "plan"}

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

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default") -> Dict[str, Any]:
        # PRESET: Ollama First for reasoning, then Cloud failover
        if task_hint in self.OLLAMA_FIRST_TASKS:
            order = [self.ollama, self.groq, self.gemini]
        else:
            # For tools like browser/search, Groq/Gemini are often better but Ollama is stable
            order = [self.ollama, self.groq, self.gemini]

        # Filter out None clients (missing API keys)
        order = [c for c in order if c is not None]

        errors = []
        for client in order:
            try:
                return await client.generate_with_tools(messages, tools)
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
        if task_hint in self.OLLAMA_FIRST_TASKS:
            order = [self.ollama, self.groq, self.gemini]
        else:
            order = [self.ollama, self.groq, self.gemini]
            
        order = [c for c in order if c is not None]

        errors = []
        for client in order:
            try:
                if hasattr(client, "generate_stream"):
                    return await client.generate_stream(messages, tools, on_token=on_token)
                else:
                    return await client.generate_with_tools(messages, tools)
            except (GroqRateLimit, GeminiRateLimit) as e:
                logger.warning(f"Model tier {client.__class__.__name__} failed with rate limit. Trying next...")
                errors.append(str(e))
                continue
            except Exception as e:
                logger.error(f"Model tier {client.__class__.__name__} failed with error: {e}")
                errors.append(str(e))
                continue
                
        raise AllModelsExhausted(f"All model tiers failed: {', '.join(errors)}")
