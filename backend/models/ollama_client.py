import logging
from typing import List, Dict, Any, Optional
import ollama
from backend.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        # Increase timeout for large model loads and complex generation (600 seconds)
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL, timeout=600)
        self.model = settings.OLLAMA_MODEL

    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        # Deep copy to avoid mutating caller's history
        messages = [msg.copy() for msg in messages]

        if tools:
            tool_descriptions = "\n".join([
                f"- {t['function']['name']}: {t['function']['description']}. Params: {t['function']['parameters']}"
                for t in tools
            ])
            system_injection = (
                "\n\nYou have access to the following tools. "
                "To use them, output only a JSON object like: "
                "{\"tool_call\": {\"name\": \"tool_name\", \"params\": {...}}}.\n"
                f"Tools:\n{tool_descriptions}"
            )
            found_system = False
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = msg["content"] + system_injection
                    found_system = True
                    break
            if not found_system:
                messages.insert(0, {"role": "system", "content": system_injection})

        try:
            chat_kwargs = {
                "model": self.model,
                "messages": messages,
                "options": {
                    "num_ctx": settings.AGENT_MAX_CONTEXT_TOKENS,
                    "num_predict": 8192
                }
            }
            if tools:
                chat_kwargs["tools"] = tools

            response = await self.client.chat(**chat_kwargs)

            content = response.message.content or ""
            thought = ""
            text = content
            tool_call = None

            if "<thought>" in content and "</thought>" in content:
                thought = content.split("<thought>")[1].split("</thought>")[0].strip()
                text = content.split("</thought>")[1].strip()

            native_tool_calls = getattr(response.message, "tool_calls", None)
            if native_tool_calls and len(native_tool_calls) > 0:
                call = native_tool_calls[0]
                if isinstance(call, dict):
                    func = call.get("function", {})
                    tool_call = {
                        "name": func.get("name", ""),
                        "params": func.get("arguments", {})
                    }
                else:
                    tool_call = {
                        "name": getattr(call.function, "name", ""),
                        "params": getattr(call.function, "arguments", {})
                    }
            else:
                import json
                text_to_parse = text.strip()
                if "```json" in text_to_parse:
                    text_to_parse = text_to_parse.split("```json")[1].split("```")[0].strip()
                elif "```" in text_to_parse:
                    text_to_parse = text_to_parse.split("```")[1].split("```")[0].strip()
                
                # Check for <tool_call> tags
                if "<tool_call>" in text_to_parse and "</tool_call>" in text_to_parse:
                    text_to_parse = text_to_parse.split("<tool_call>")[1].split("</tool_call>")[0].strip()

                start = text_to_parse.find("{")
                end = text_to_parse.rfind("}") + 1
                if start != -1 and end != -1:
                    json_str = text_to_parse[start:end]
                    try:
                        data = json.loads(json_str, strict=False)
                        logger.info(f"Parsed JSON from Ollama fallback: (keys: {list(data.keys())})")
                        
                        if "tool_call" in data:
                            tool_call = data["tool_call"]
                            text = ""
                        elif "name" in data and ("params" in data or "arguments" in data):
                            tool_call = {
                                "name": data["name"],
                                "params": data.get("params") or data.get("arguments")
                            }
                            text = ""
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON from Ollama fallback: {e}")

            return {
                "model_used": "ollama",
                "thought": thought,
                "tool_call": tool_call,
                "text": text,
                "tokens_used": 0
            }

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise e
