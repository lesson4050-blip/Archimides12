import logging
from typing import List, Dict, Any, Optional, Callable
import ollama
from backend.config import settings
from backend.utils.json_repair import repair_and_parse
from backend.utils.tool_schemas import validate_tool_call, fuzzy_match_tool_name

logger = logging.getLogger(__name__)

MAX_TOOL_CALL_RETRIES = 3


OLLAMA_TIMEOUT_MAP = {
    "qwen2.5:14b": 600.0,
    "qwen2.5:32b": 900.0,
    "qwen2.5-coder:14b": 600.0,
    "qwen2.5:72b": 1200.0,
    "qwen2.5:7b": 300.0,
    "default": 600.0
}

class OllamaClient:
    def __init__(self, model: Optional[str] = None):
        # We will instantiate client dynamically in _get_client based on model to use OLLAMA_TIMEOUT_MAP
        self.model = model or settings.OLLAMA_MODEL

    def _get_client(self, model_name: str) -> ollama.AsyncClient:
        timeout = OLLAMA_TIMEOUT_MAP.get(model_name, OLLAMA_TIMEOUT_MAP["default"])
        return ollama.AsyncClient(host=settings.OLLAMA_BASE_URL, timeout=timeout)

    # Task-specific model selection (if multiple models installed)
    TASK_MODELS = {
        "think": "qwen2.5:14b",
        "plan": "qwen2.5:14b",
        "code": "qwen2.5:14b",
        "fast": "qwen2.5:14b",
        "summarize": "qwen2.5:14b",
    }

    def _select_model(self, task_hint: str = "default") -> str:
        """Select optimal Ollama model based on task type.
        Falls back to default model if task-specific model is not available."""
        preferred = self.TASK_MODELS.get(task_hint)
        if preferred:
            return preferred
        return self.model

    def _get_available_tool_names(
        self, tools: Optional[List[Dict]]
    ) -> List[str]:
        if not tools:
            return []
        return [t["function"]["name"] for t in tools if "function" in t]

    def _build_tool_system_injection(
        self, tools: List[Dict[str, Any]]
    ) -> str:
        """
        Build a clear, small-model-friendly tool instruction.
        Uses few-shot examples to maximize reliability.
        """
        tool_list = []
        for t in tools:
            f = t.get("function", {})
            params = f.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            param_desc = ", ".join([
                f'"{k}": <{v.get("type","any")}>'
                + (" (required)" if k in required else " (optional)")
                for k, v in props.items()
            ])
            tool_list.append(
                f'  • {f["name"]}: {f.get("description","")}\n'
                f'    Params: {{{param_desc}}}'
            )

        tools_text = "\n".join(tool_list)

        return f"""
AVAILABLE TOOLS:
{tools_text}

TO CALL A TOOL, output ONLY this JSON (nothing else, no explanation):
{{"tool_call": {{"name": "tool_name", "params": {{...}}}}}}

EXAMPLES:
{{"tool_call": {{"name": "shell", "params": {{"action": "exec", "command": "ls -la"}}}}}}
{{"tool_call": {{"name": "file", "params": {{"action": "write", "path": "/tmp/test.py", "content": "print('hello')"}}}}}}
{{"tool_call": {{"name": "search", "params": {{"query": "latest AI news"}}}}}}

If you don't need a tool, respond normally in plain text.
NEVER mix tool JSON with explanation text.
"""

    async def _call_model(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> Any:
        chat_kwargs = {
            "model": self._select_model(getattr(self, "_current_task_hint", "default")),
            "messages": messages,
            "options": {
                "num_ctx": min(
                    settings.AGENT_MAX_CONTEXT_TOKENS, 32768
                ),
                "num_predict": max_tokens,
                "temperature": temperature,
                "num_gpu": 999,
                "num_thread": 8,
                "keep_alive": "10m",
            }
        }

        # IMPORTANT: Do NOT apply format=json globally.
        # Only apply when specifically needed for plan generation.
        # For tool calls, we use text injection — format=json
        # would break conversational text responses.
        #
        # The format parameter is handled separately in generate_with_tools()
        # only when force_json_schema is provided and no tools are present.

        if tools:
            chat_kwargs["tools"] = tools

        # Only pass native tools if Ollama supports them for this model
        # We use text injection as primary method for reliability
        client = self._get_client(chat_kwargs["model"])
        return await client.chat(**chat_kwargs)


    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        force_json_schema: Optional[Dict] = None,
        task_hint: str = "default",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        self._current_task_hint = task_hint

        messages = [msg.copy() for msg in messages]
        available_names = self._get_available_tool_names(tools)

        # Inject tool instructions into system prompt
        if tools:
            injection = self._build_tool_system_injection(tools)
            injected = False
            for msg in messages:
                if msg["role"] == "system":
                    # Use prefix cache pattern: append only new info
                    if "AVAILABLE TOOLS:" not in msg["content"]:
                        msg["content"] = msg["content"] + "\n\n" + injection
                    injected = True
                    break
            if not injected:
                messages.insert(0, {
                    "role": "system", "content": injection
                })

        # Apply format ONLY for schema-constrained generation (no tools)
        if force_json_schema and not tools:
            # Will be passed to _call_model via a modified path
            pass  # Handled below

        last_error = None
        for attempt in range(MAX_TOOL_CALL_RETRIES):
            try:
                # If force_json_schema and no tools, apply format constraint
                if force_json_schema and not tools:
                    chat_kwargs = {
                        "model": self._select_model(getattr(self, "_current_task_hint", "default")),
                        "messages": messages,
                        "format": force_json_schema,
                        "options": {
                            "num_ctx": min(
                                settings.AGENT_MAX_CONTEXT_TOKENS, 16384
                            ),
                            "num_predict": max_tokens,
                            "temperature": temperature,
                            "num_gpu": 999,
                            "num_thread": 8,
                            "keep_alive": "10m",
                        }
                    }
                    client = self._get_client(chat_kwargs["model"])
                    response = await client.chat(**chat_kwargs)
                else:
                    response = await self._call_model(messages, tools, temperature=temperature, max_tokens=max_tokens)

                content = response.message.content or ""

                # Extract thought block
                thought = ""
                text = content
                
                # Check for <thinking> or <thought>
                thinking_tags = [("<thinking>", "</thinking>"), ("<thought>", "</thought>")]
                for start_tag, end_tag in thinking_tags:
                    if start_tag in content and end_tag in content:
                        thought = content.split(start_tag)[1].split(end_tag)[0].strip()
                        text = content.split(end_tag)[-1].strip()
                        break

                # Try native tool calls first (newer Ollama versions)
                native_calls = getattr(
                    response.message, "tool_calls", None
                )
                tool_call = None

                if native_calls:
                    call = native_calls[0]
                    if isinstance(call, dict):
                        func = call.get("function", {})
                        raw_tc = {
                            "name": func.get("name", ""),
                            "params": func.get("arguments", {})
                        }
                    else:
                        raw_tc = {
                            "name": getattr(call.function, "name", ""),
                            "params": getattr(
                                call.function, "arguments", {}
                            )
                        }
                    validated = validate_tool_call(raw_tc)
                    if validated:
                        tool_call = validated.model_dump()

                # Fallback: parse from text content
                if tool_call is None and text.strip():
                    # 1. Try standard JSON tool_call format
                    parsed, err = repair_and_parse(text.strip())
                    if parsed and isinstance(parsed, dict):
                        if "tool_call" in parsed:
                            validated = validate_tool_call(parsed["tool_call"])
                            if validated:
                                tool_call = validated.model_dump()
                                text = ""
                        elif "name" in parsed and ("params" in parsed or "arguments" in parsed):
                            raw_tc = {
                                "name": parsed["name"],
                                "params": parsed.get("params") or parsed.get("arguments", {})
                            }
                            validated = validate_tool_call(raw_tc)
                            if validated:
                                tool_call = validated.model_dump()
                                text = ""
                    
                    # 2. Try XML-style format: /function name>params</function>
                    if tool_call is None:
                        import re
                        xml_match = re.search(r"/function\s+(\w+)\s*>(.*?)</function>", text, re.DOTALL)
                        if xml_match:
                            t_name = xml_match.group(1)
                            t_args_str = xml_match.group(2)
                            t_args, _ = repair_and_parse(t_args_str)
                            if isinstance(t_args, dict):
                                validated = validate_tool_call({"name": t_name, "params": t_args})
                                if validated:
                                    tool_call = validated.model_dump()
                                    text = ""

                # Fuzzy match tool name if needed
                if tool_call and available_names:
                    matched = fuzzy_match_tool_name(
                        tool_call["name"], available_names
                    )
                    if matched:
                        tool_call["name"] = matched
                    elif tool_call["name"] not in available_names:
                        # Model hallucinated a tool name, retry
                        logger.warning(
                            f"Unknown tool '{tool_call['name']}'. "
                            f"Available: {available_names}. "
                            f"Retry {attempt+1}/{MAX_TOOL_CALL_RETRIES}"
                        )
                        error_msg = (
                            f"Tool '{tool_call['name']}' does not exist. "
                            f"Available tools: {available_names}. "
                            f"Please use one of those."
                        )
                        messages.append({
                            "role": "assistant",
                            "content": content
                        })
                        messages.append({
                            "role": "user",
                            "content": error_msg
                        })
                        tool_call = None
                        continue

                return {
                    "model_used": "ollama",
                    "thinking": thought,
                    "tool_call": tool_call,
                    "text": text,
                    "tokens_used": 0
                }

            except Exception as e:
                logger.error(f"Ollama error (attempt {attempt+1}): {e}")
                last_error = e
                if attempt < MAX_TOOL_CALL_RETRIES - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Ollama failed after {MAX_TOOL_CALL_RETRIES} attempts: "
            f"{last_error}"
        )

    async def generate_stream(self, messages, tools=None, on_token=None, task_hint="default", temperature: float = 0.7, max_tokens: int = 4096, **kwargs):
        if tools:
            # Can't stream with tools reliably — use non-stream
            return await self.generate_with_tools(messages, tools, task_hint=task_hint, temperature=temperature, max_tokens=max_tokens)

        # True streaming for non-tool responses
        messages = [msg.copy() for msg in messages]
        try:
            client = self._get_client(self.model)
            stream = await client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "num_ctx": min(settings.AGENT_MAX_CONTEXT_TOKENS, 32768),
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "num_gpu": 999,
                    "keep_alive": "10m",
                }
            )
            full_text = ""
            async for chunk in stream:
                token = chunk.message.content or ""
                if token:
                    full_text += token
                    if on_token:
                        await on_token(token)

            return {
                "model_used": "ollama",
                "thought": "",
                "tool_call": None,
                "text": full_text,
                "tokens_used": 0
            }
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            return await self.generate_with_tools(messages, None)
