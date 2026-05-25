import asyncio
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from backend.config import settings

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    pass

def _strip_cache_control(messages: list) -> list:
    """Remove Anthropic-specific fields that Groq rejects."""
    clean = []
    for msg in messages:
        m = dict(msg)
        if isinstance(m.get("content"), list):
            # Content blocks format
            m["content"] = [
                {k: v for k, v in block.items() if k != "cache_control"}
                for block in m["content"]
            ]
        elif isinstance(m.get("content"), dict):
            m["content"] = {k: v for k, v in m["content"].items() if k != "cache_control"}
        # Also strip top-level cache_control if present
        m.pop("cache_control", None)
        clean.append(m)
    return clean

def _parse_failed_generation(content: str) -> List[Dict[str, Any]]:
    """Parse XML-style tool calls from any string content, handling multiple tag formats."""
    import re
    import json
    from backend.utils.json_repair import repair_and_parse
    from backend.utils.tool_schemas import validate_tool_call

    # Patterns to try:
    # 1. <function=name>{args}(</function>)?
    # 2. <name>{args}(</name>)?
    # We use a combined regex that matches both formats
    # Pattern explanation: matches <(function=)?NAME>{ARGS}(</(function=)?NAME>)?
    pattern = re.compile(
        r'<(?:function=)?(?P<name>[a-zA-Z0-9_-]+)>(?P<args>.*?)(?:</(?:function=)?(?P=name)>|(?=<[a-zA-Z0-9_-]+[=>])|$)', 
        re.DOTALL
    )
    
    matches = pattern.finditer(content)
    
    tool_calls = []
    # Known tool names to avoid false positives on random XML tags
    KNOWN_TOOLS = {"search", "shell", "file", "ast_navigator", "fast_linter", "web_read", "browser", "message"}
    
    for match in matches:
        try:
            name = match.group("name").strip()
            raw_args = match.group("args").strip()
            
            if not raw_args:
                continue

            # Basic heuristic: if it's not a known tool and doesn't look like JSON, skip it
            if name not in KNOWN_TOOLS and not (raw_args.startswith('{') or '"' in raw_args):
                continue

            # Cleanup
            raw_args = re.sub(r'[;,]\s*$', '', raw_args)
            normalized_args = raw_args.replace(": True", ": true").replace(": False", ": false").replace(": None", ": null")
            
            # Repair and parse
            parsed_args, _ = repair_and_parse(normalized_args)
            if not parsed_args or not isinstance(parsed_args, dict):
                # Try manual cleanup
                clean_args = re.sub(r'#.*$', '', normalized_args, flags=re.MULTILINE)
                last_brace = clean_args.rfind('}')
                if last_brace != -1:
                    clean_args = clean_args[:last_brace+1]
                try:
                    parsed_args = json.loads(clean_args)
                except:
                    continue
            
            if parsed_args:
                # Type Coercion
                for k, v in parsed_args.items():
                    if k in ["max_results", "num_results", "limit", "count"] and isinstance(v, str):
                        try:
                            parsed_args[k] = int(v)
                        except: pass
                    if isinstance(v, str) and v.lower() in ("true", "false"):
                        parsed_args[k] = (v.lower() == "true")
                
                raw_tc = {"name": name, "params": parsed_args}
                validated = validate_tool_call(raw_tc)
                if validated:
                    tool_calls.append(validated.model_dump())
                else:
                    # Even if validation fails, return it (orchestrator might fix it or we use defaults)
                    tool_calls.append(raw_tc)
        except Exception as e:
            logger.debug(f"Failed to parse individual tool call match: {e}")
            continue
    
    return tool_calls

class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        task_hint: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        retries = 0
        backoff = 2
        
        while retries < 3:
            try:
                import json
                
                formatted_messages = []
                for i, msg in enumerate(_strip_cache_control(messages)):
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
                            
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                message = response.choices[0].message
                thought = ""
                
                tool_calls = []
                if message.tool_calls:
                    from backend.utils.tool_schemas import validate_tool_call
                    from backend.utils.json_repair import repair_and_parse
                    for tc in message.tool_calls:
                        raw_args = tc.function.arguments
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
                        if validated:
                            tool_calls.append(validated.model_dump())
                        else:
                            tool_calls.append(raw_tc)

                if not tool_calls and message.content:
                    tool_calls = _parse_failed_generation(message.content)
                
                return {
                    "model_used": "groq",
                    "thought": thought,
                    "tool_calls": tool_calls,
                    "text": message.content or "",
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                }
                
            except Exception as e:
                err_str = str(e)
                if "tool_use_failed" in err_str or "failed_generation" in err_str:
                    logger.warning(f"Groq tool_use_failed detected. Attempting rescue. Error: {err_str[:200]}...")
                    try:
                        # Extract unescaped failed_generation directly from exception body if available
                        failed_gen = ""
                        if hasattr(e, "body") and isinstance(e.body, dict):
                            failed_gen = e.body.get("error", {}).get("failed_generation", "")
                        if not failed_gen and hasattr(e, "response") and hasattr(e.response, "json"):
                            try:
                                failed_gen = e.response.json().get("error", {}).get("failed_generation", "")
                            except Exception:
                                pass
                        
                        source_str = failed_gen if failed_gen else err_str
                        tool_calls = _parse_failed_generation(source_str)
                        if tool_calls:
                            logger.info(f"Successfully rescued {len(tool_calls)} tool calls from error string")
                            return {
                                "model_used": "groq",
                                "thought": "Rescued from tool_use_failed",
                                "tool_calls": tool_calls,
                                "text": "",
                                "tokens_used": 0
                            }
                        else:
                            # Text-rescue fallback: if no valid tool calls, extract clean text/code
                            import re
                            text_content = ""
                            if failed_gen:
                                text_content = failed_gen
                                text_content = re.sub(r'<message>(.*?)</message>', r'\1', text_content, flags=re.DOTALL)
                                text_content = re.sub(r'</?[a-zA-Z0-9_-]+(?:=[^>]+)?>', '', text_content)
                                text_content = text_content.strip()
                            
                            if text_content:
                                logger.info("Successfully rescued text content from failed generation")
                                return {
                                    "model_used": "groq",
                                    "thought": "Rescued text response from tool_use_failed",
                                    "tool_calls": [],
                                    "text": text_content,
                                    "tokens_used": 0
                                }
                            
                            logger.warning("Rescue failed: no valid tool calls or text found in error string.")
                    except Exception as rescue_err:
                        logger.error(f"Failed to rescue Groq tool call: {rescue_err}")

                if "429" in err_str or "rate_limit" in err_str.lower():
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

        model = self.model
        
        formatted_messages = []
        for msg in _strip_cache_control(messages):
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
                    response.raise_for_status()
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
            return await self.generate_with_tools(messages, tools=tools)

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
