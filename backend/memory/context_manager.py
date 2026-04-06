import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages short-term memory: conversation history and summarization.
    """
    def __init__(self, max_tokens: int = 16384, summarization_threshold: int = 12000):
        self.history: List[Dict[str, Any]] = []
        self.max_tokens = max_tokens
        self.summarization_threshold = summarization_threshold
        self.current_tokens = 0

    def add_message(self, role: str, content: str, **kwargs):
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.history.append(message)
        # Update current_tokens heuristic (approx 4 chars per token)
        self.current_tokens += len(content) // 4

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.history

    async def summarize_if_needed(self, model_router: Any):
        """
        If tokens exceed threshold, summarize oldest 50% of history.
        """
        if self.current_tokens < self.summarization_threshold:
            return

        logger.info(f"Context threshold reached ({self.current_tokens} tokens). Summarizing...")
        
        # Keep system prompt (index 0) and last 10 messages
        system_prompt = self.history[0] if self.history and self.history[0]["role"] == "system" else None
        
        to_summarize = self.history[1:-10]
        recent = self.history[-10:]
        
        if not to_summarize:
            return

        summary_prompt = "Summarize the following conversation history into one concise paragraph, preserving all key facts, code locations, and decisions made:\n\n"
        for msg in to_summarize:
            summary_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
            
        try:
            # Use Gemini for summarization as per spec
            response = await model_router.generate(
                messages=[{"role": "user", "content": summary_prompt}],
                task_hint="summarize"
            )
            summary_text = response.get("text", "Conversation summary unavailable.")
            
            # Reconstruct history
            new_history = []
            if system_prompt:
                new_history.append(system_prompt)
            new_history.append({"role": "system", "content": f"Previous conversation summary: {summary_text}"})
            new_history.extend(recent)
            
            self.history = new_history
            # Reset token count and re-calculate
            self.current_tokens = sum(len(m["content"]) for m in self.history) // 4
            logger.info("Summarization complete.")
            
        except Exception as e:
            logger.error(f"Failed to summarize context: {e}")
