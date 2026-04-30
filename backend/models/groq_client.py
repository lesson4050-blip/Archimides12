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

    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default", **kwargs) -> Dict[str, Any]:
        retries = 0
        backoff = 2
        
        while retries < 3:
            try:
                import json
                
                # Transform messages: Groq requires stringified arguments in tool_calls
                formatted_messages = []
                for i, msg in enumerate(messages):
                    new_msg = msg.copy()
                    # Mark first system message for prefix caching (Groq supports this)
                    if msg.get("role") == "system" and i == 0:
                        new_msg["cache_control"] = {"type": "ephemeral"}
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
                    from backend.utils.tool_schemas import validate_tool_call
                    from backend.utils.json_repair import repair_and_parse
                    raw_args = tc.function.arguments
                    # Try native parse first, then repair
                    try:
                        parsed_args = json.loads(raw_args)
                    except Exception:
                        parsed_args, _ = repair_and_parse(raw_args)
                        parsed_args = parsed_args or {}
                    raw_tc = {
                        "name": tc.function.name,
                        "params": parsed_args
                    }
                    validated = validate_tool_call(raw_tc)
                    tool_call = validated.model_dump() if validated else None

                # Also check text content for embedded tool calls
                # (some Groq models put tool calls in text)
                if tool_call is None and message.content:
                    from backend.utils.json_repair import repair_and_parse
                    from backend.utils.tool_schemas import validate_tool_call
                    parsed, _ = repair_and_parse(message.content)
                    if parsed and isinstance(parsed, dict):
                        if "tool_call" in parsed:
                            validated = validate_tool_call(parsed["tool_call"])
                            if validated:
                                tool_call = validated.model_dump()                
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

    async def generate_stream(
        self, 
        messages: list, 
        tools: list = None, 
        on_token=None,
        task_hint: str = "default",
        **kwargs
    ) -> dict:
        """True token-by-token streaming from Groq API."""
        import httpx
        import json

        # We assume self.model is set
        model = self.model
        
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

        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        full_text = ""
        tool_call_accumulator = {}

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})

                            token = delta.get("content", "")
                            if token:
                                full_text += token
                                if on_token:
                                    await on_token({
                                        "type": "token",
                                        "content": token
                                    })

                            if "tool_calls" in delta:
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_call_accumulator:
                                        tool_call_accumulator[idx] = {
                                            "name": "", "arguments": ""
                                        }
                                    fn = tc.get("function", {})
                                    if fn.get("name"):
                                        tool_call_accumulator[idx]["name"] += fn["name"]
                                    if fn.get("arguments"):
                                        tool_call_accumulator[idx]["arguments"] += fn["arguments"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as e:
            logger.error(f"Groq stream error: {e}")
            # Fallback to non-streaming
            return await self.generate_with_tools(messages, tools=tools)

        # Parse accumulated tool call
        tool_call = None
        if tool_call_accumulator:
            tc = tool_call_accumulator[0]
            try:
                params = json.loads(tc["arguments"]) if tc["arguments"] else {}
                tool_call = {"name": tc["name"], "params": params}
            except json.JSONDecodeError:
                pass

        return {
            "text": full_text,
            "tool_call": tool_call,
            "model_used": model
        }
