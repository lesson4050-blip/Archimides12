import logging
from typing import List, Dict, Any, Optional
from backend.models.groq_client import GroqClient, RateLimitExceeded as GroqRateLimit
from backend.models.gemini_client import GeminiClient, RateLimitExceeded as GeminiRateLimit
from backend.models.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class AllModelsExhausted(Exception):
    pass

class ModelRouter:
    # Tasks that require Gemini's quality (long context, browser, research)
    GEMINI_FIRST_TASKS = {"browser", "search", "result", "summarize"}
    # Tasks that benefit from Gemma 4's native reasoning via Ollama
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
        if task_hint in self.GEMINI_FIRST_TASKS:
            order = [self.gemini, self.groq, self.ollama]
        elif task_hint in self.OLLAMA_FIRST_TASKS:
            order = [self.ollama, self.groq, self.gemini]
        else:
            order = [self.groq, self.gemini, self.ollama]

        # Filter out None clients (missing API keys)
        order = [c for c in order if c is not None]

        errors = []
        for client in order:
            try:
                # We need to make sure tool format is normalized? 
                # Groq and Gemini clients should handle their respective formats.
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
