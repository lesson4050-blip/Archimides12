import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AnthropicClient:
    """Simple wrapper for Anthropic Claude models."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.default_model = "claude-3-5-sonnet-20241022"
        self._client = None
        
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
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
                system=system_prompt.strip() if system_prompt else anthropic.NOT_GIVEN,
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
            
    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:
        """Wrapper for generate_with_tools, ignoring tools for now."""
        # TODO: Implement native tool calling for Anthropic
        result = await self.generate(messages, **kwargs)
        return {
            "model_used": "anthropic",
            "thinking": "",
            "tool_call": None,
            "text": result.get("text", ""),
            "tokens_used": result.get("usage", {}).get("completion_tokens", 0)
        }
        
    async def generate_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, on_token=None, **kwargs) -> Dict[str, Any]:
        """Wrapper for streaming, falls back to non-streaming for now."""
        # TODO: Implement streaming for Anthropic
        result = await self.generate_with_tools(messages, tools, **kwargs)
        if on_token and result.get("text"):
            await on_token({"type": "token", "content": result.get("text")})
        return result
