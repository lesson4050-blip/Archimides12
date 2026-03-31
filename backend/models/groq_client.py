import asyncio
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from backend.config import settings

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    pass

class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        retries = 0
        backoff = 2
        
        while retries < 3:
            try:
                import json
                
                # Transform messages: Groq requires stringified arguments in tool_calls
                formatted_messages = []
                for msg in messages:
                    new_msg = msg.copy()
                    if "tool_calls" in new_msg and new_msg["tool_calls"]:
                        new_tool_calls = []
                        for tc in new_msg["tool_calls"]:
                            new_tc = tc.copy()
                            if "function" in new_tc:
                                new_func = new_tc["function"].copy()
                                if isinstance(new_func.get("arguments"), dict):
                                    new_func["arguments"] = json.dumps(new_func["arguments"])
                                new_tc["function"] = new_func
                            new_tool_calls.append(new_tc)
                        new_msg["tool_calls"] = new_tool_calls
                    formatted_messages.append(new_msg)
                
                # Ensure all tools have 'type': 'function' for Groq
                if tools:
                    for t in tools:
                        if "type" not in t:
                            t["type"] = "function"
                            
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                )
                
                message = response.choices[0].message
                thought = ""
                # Some models support reasoning_content or similar, Groq Llama 3.3 might not directly, 
                # but we'll try to extract from text if it's there or just leave empty for now as per unified format.
                
                tool_call = None
                if message.tool_calls:
                    tc = message.tool_calls[0]
                    import json
                    tool_call = {
                        "name": tc.function.name,
                        "params": json.loads(tc.function.arguments)
                    }
                
                return {
                    "model_used": "groq",
                    "thought": thought,
                    "tool_call": tool_call,
                    "text": message.content or "",
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                }
                
            except Exception as e:
                # Check for 429
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    logger.warning(f"Groq Rate Limit hit. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                else:
                    logger.error(f"Groq API error: {e}")
                    raise e
                    
        raise RateLimitExceeded("Groq Rate Limit exceeded after 3 attempts")
