import logging
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.config import settings

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    pass

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model_name = settings.GEMINI_MODEL

    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        retries = 0
        backoff = 2
        
        # Prepare content from messages
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
                
            role = "user" if msg["role"] == "user" else "model"
            parts = []
            
            # Text part
            if msg.get("content"):
                parts.append(types.Part(text=msg["content"]))
                
            # Tool calls part (assistant role)
            if msg["role"] == "assistant" and "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    parts.append(types.Part(
                        function_call=types.FunctionCall(
                            name=tc["function"]["name"],
                            args=tc["function"]["arguments"]
                        )
                    ))
            
            # Tool result part (tool role)
            if msg["role"] == "tool":
                role = "user" # Tool results are sent as 'user' (or 'function' part in user) in Gemini
                parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=msg["name"],
                        response={"result": msg["content"]}
                    )
                ))
                
            if parts:
                contents.append(types.Content(role=role, parts=parts))

        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
                break

        # Prepare tools
        genai_tools = []
        if tools:
            # New SDK can take OpenAI-style function declarations directly in some cases,
            # but let's be safe and wrap them if needed.
            # Actually, the new SDK's GenerateContentConfig.tools expectation is a list of Tool objects
            fns = []
            for t in tools:
                if t.get("type") == "function":
                    f = t["function"]
                    fns.append(types.FunctionDeclaration(
                        name=f["name"],
                        description=f["description"],
                        parameters=f["parameters"]
                    ))
            if fns:
                genai_tools = [types.Tool(function_declarations=fns)]

        while retries < 3:
            try:
                # Use generate_content
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        tools=genai_tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True # We handle it in our loop
                        )
                    )
                )

                # Extract content
                tool_call = None
                text_content = ""
                
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.text:
                            text_content += part.text
                        if part.function_call:
                            tool_call = {
                                "name": part.function_call.name,
                                "params": dict(part.function_call.args) if part.function_call.args else {}
                            }

                return {
                    "model_used": "gemini",
                    "thought": "", # Extract thought if tags are used
                    "tool_call": tool_call,
                    "text": text_content,
                    "tokens_used": response.usage_metadata.total_token_count if response.usage_metadata else 0
                }

            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "503" in err_msg or "quota" in err_msg:
                    logger.warning(f"Gemini Rate Limit hit. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                else:
                    logger.error(f"Gemini API error: {e}")
                    raise e
                    
        raise RateLimitExceeded("Gemini Rate Limit exceeded")
