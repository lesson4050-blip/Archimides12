import logging
from typing import List, Dict, Any, Optional
import ollama
from backend.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        # Increase timeout for large model loads (300 seconds)
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL, timeout=300)
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
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "num_ctx": settings.AGENT_MAX_CONTEXT_TOKENS,
                    "num_predict": 4096
                }
            )

            content = response.message.content
            thought = ""
            text = content
            tool_call = None

            if "<thought>" in content and "</thought>" in content:
                thought = content.split("<thought>")[1].split("</thought>")[0].strip()
                text = content.split("</thought>")[1].strip()

            import json
            if "{" in text and "}" in text:
                try:
                    # Try to find JSON block, possibly inside markdown code blocks
                    json_text = text
                    if "```json" in text:
                        json_text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        json_text = text.split("```")[1].split("```")[0]
                    
                    start = json_text.find("{")
                    end = json_text.rfind("}") + 1
                    if start != -1 and end != -1:
                        json_str = json_text[start:end]
                        data = json.loads(json_str)
                        logger.info(f"Parsed JSON from Ollama: {data}")
                        
                        if "tool_call" in data:
                            tool_call = data["tool_call"]
                            # Keep only text BEFORE the tool call
                            text = text.split(json_str)[0].strip()
                        elif "name" in data and ("params" in data or "arguments" in data):
                            tool_call = {
                                "name": data["name"],
                                "params": data.get("params") or data.get("arguments")
                            }
                            text = text.split(json_str)[0].strip()
                except Exception as e:
                    logger.warning(f"Failed to parse JSON from Ollama output: {e}")
                    pass

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
