import logging
import os
from typing import Dict, Any, List, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)
class AnthropicClient:
    """Simple wrapper for Anthropic Claude models."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.default_model = "claude-3-5-sonnet-20241022"
        self._client = None
        
        if self.api_key:
            if anthropic is not None:
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            else:
                logger.warning("anthropic library not installed. Claude support disabled.")
    
    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate response using Claude."""
        if not self.is_available:
            raise ValueError("Anthropic API key not configured or library missing")
            
        try:
            # Convert internal messages format to Anthropic format
            system_prompt = ""
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt += msg["content"] + "\n"
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            response = await self._client.messages.create(
                model=kwargs.get("model", self.default_model),
                system=system_prompt.strip() if system_prompt else (anthropic.NOT_GIVEN if anthropic else None),
                messages=anthropic_messages,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.7)
            )
            
            # Simple text extraction for basic completion
            text = ""
            for block in response.content:
                if block.type == "text":
                    text += block.text
                    
            return {
                "text": text,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
            
    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate with native Anthropic tool calling."""
        if not self.is_available:
            raise ValueError("Anthropic client unavailable")

        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompt += content + "\n"
            elif role in ("user", "assistant"):
                if content:
                    anthropic_messages.append({"role": role, "content": content})
            elif role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": f"Tool result: {content}"
                })

        if not anthropic_messages:
            anthropic_messages = [{"role": "user", "content": "Continue."}]

        import anthropic as anthropic_lib

        # Convert OpenAI-style tools to Anthropic format
        anthropic_tools = []
        if tools:
            for tool in tools:
                if tool.get("type") == "function":
                    fn = tool["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object"})
                    })

        create_kwargs = dict(
            model=kwargs.get("model", self.default_model),
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        if system_prompt.strip():
            create_kwargs["system"] = system_prompt.strip()
        if anthropic_tools:
            create_kwargs["tools"] = anthropic_tools

        try:
            response = await self._client.messages.create(**create_kwargs)

            text = ""
            tool_call = None

            for block in response.content:
                if block.type == "text":
                    text += block.text
                elif block.type == "tool_use":
                    tool_call = {
                        "name": block.name,
                        "params": block.input or {}
                    }

            return {
                "model_used": response.model,
                "thinking": "",
                "tool_call": tool_call,
                "text": text,
                "tokens_used": response.usage.output_tokens
            }
        except Exception as e:
            logger.error(f"Anthropic generate_with_tools error: {e}")
            raise

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_token=None,
        **kwargs
    ) -> Dict[str, Any]:
        """True streaming from Anthropic API."""
        if not self.is_available:
            raise ValueError("Anthropic client unavailable")

        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompt += content + "\n"
            elif role in ("user", "assistant") and content:
                anthropic_messages.append({"role": role, "content": content})

        if not anthropic_messages:
            anthropic_messages = [{"role": "user", "content": "Continue."}]

        full_text = ""
        create_kwargs = dict(
            model=kwargs.get("model", self.default_model),
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        if system_prompt.strip():
            create_kwargs["system"] = system_prompt.strip()

        try:
            async with self._client.messages.stream(**create_kwargs) as stream:
                async for text_chunk in stream.text_stream:
                    full_text += text_chunk
                    if on_token:
                        await on_token({"type": "token", "content": text_chunk})

            return {
                "model_used": self.default_model,
                "thinking": "",
                "tool_call": None,
                "text": full_text,
                "tokens_used": len(full_text.split())
            }
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}, falling back")
            return await self.generate_with_tools(messages, tools, **kwargs)
