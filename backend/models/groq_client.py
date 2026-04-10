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

    async def generate_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, on_token=None) -> Dict[str, Any]:
        retries = 0
        backoff = 2
        
        while retries < 3:
            try:
                import json
                
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
                
                if tools:
                    for t in tools:
                        if "type" not in t:
                            t["type"] = "function"
                
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    tools=tools or [],
                    tool_choice="auto" if tools else "none",
                    stream=True
                )
                
                full_text = ""
                tool_call_data = {}
                
                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta: continue
                    
                    if delta.content:
                        full_text += delta.content
                        if on_token:
                            await on_token({"type": "token", "content": delta.content})
                    
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_call_data:
                                tool_call_data[idx] = {"name": "", "arguments": ""}
                            if tc.function and tc.function.name:
                                tool_call_data[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_call_data[idx]["arguments"] += tc.function.arguments
                
                result = {"text": full_text, "model_used": "groq", "thought": "", "tool_call": None, "tokens_used": 0}
                if tool_call_data:
                    # We assume it only uses the first tool call
                    tc = list(tool_call_data.values())[0]
                    try:
                        result["tool_call"] = {
                            "name": tc["name"],
                            "params": json.loads(tc["arguments"])
                        }
                    except Exception as e:
                        logger.warning(f"Failed to parse streamed tool args: {e}")
                
                # Extract thought if present in <thought> tags
                if "<thought>" in full_text and "</thought>" in full_text:
                    thought_start = full_text.find("<thought>") + 9
                    thought_end = full_text.find("</thought>")
                    if thought_end > thought_start:
                        result["thought"] = full_text[thought_start:thought_end].strip()
                        
                return result
                
            except Exception as e:
                # Check for rate limits
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    logger.warning(f"Groq Rate Limit hit. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                else:
                    logger.error(f"Groq API stream error: {e}")
                    raise e
                    
        raise RateLimitExceeded("Groq Rate Limit exceeded after 3 attempts")
