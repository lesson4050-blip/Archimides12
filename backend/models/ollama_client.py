import logging
from typing import List, Dict, Any, Optional
import ollama
from backend.config import settings
from backend.utils.json_repair import repair_and_parse
from backend.utils.tool_schemas import validate_tool_call, fuzzy_match_tool_name

logger = logging.getLogger(__name__)

MAX_TOOL_CALL_RETRIES = 3


class OllamaClient:
    def __init__(self):
        self.client = ollama.AsyncClient(
            host=settings.OLLAMA_BASE_URL, timeout=600
        )
        self.model = settings.OLLAMA_MODEL

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
        tools: Optional[List[Dict]] = None
    ) -> Any:
        chat_kwargs = {
            "model": self.model,
            "messages": messages,
            "options": {
                "num_ctx": min(
                    settings.AGENT_MAX_CONTEXT_TOKENS, 16384
                ),
                "num_predict": 4096,
                "temperature": 0.1,
            }
        }
        # Only pass native tools if Ollama supports them for this model
        # We use text injection as primary method for reliability
        return await self.client.chat(**chat_kwargs)

    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:

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

        last_error = None
        for attempt in range(MAX_TOOL_CALL_RETRIES):
            try:
                response = await self._call_model(messages, tools)
                content = response.message.content or ""

                # Extract thought block
                thought = ""
                text = content
                if "<thought>" in content and "</thought>" in content:
                    thought = (
                        content.split("<thought>")[1]
                        .split("</thought>")[0].strip()
                    )
                    text = content.split("</thought>")[-1].strip()

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
                    parsed, err = repair_and_parse(text.strip())
                    if parsed and isinstance(parsed, dict):
                        if "tool_call" in parsed:
                            validated = validate_tool_call(
                                parsed["tool_call"]
                            )
                            if validated:
                                tool_call = validated.model_dump()
                                text = ""
                        elif "name" in parsed and (
                            "params" in parsed or "arguments" in parsed
                        ):
                            raw_tc = {
                                "name": parsed["name"],
                                "params": parsed.get("params")
                                or parsed.get("arguments", {})
                            }
                            validated = validate_tool_call(raw_tc)
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
                    "thought": thought,
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

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_token=None
    ) -> Dict[str, Any]:
        # For streaming, fall back to non-streaming for tool calls
        # to ensure JSON integrity
        result = await self.generate_with_tools(messages, tools)
        if on_token and result.get("text"):
            await on_token({
                "type": "token",
                "content": result["text"]
            })
        return result
