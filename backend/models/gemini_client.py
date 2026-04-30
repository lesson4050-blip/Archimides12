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

    async def generate_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, task_hint: str = "default") -> Dict[str, Any]:
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

        # Route model based on task complexity
        if task_hint in ("think", "plan"):
            selected_model = "gemini-1.5-pro"
        elif task_hint in ("quick", "default"):
            selected_model = "gemini-1.5-flash"
        else:
            selected_model = self.model_name

        while retries < 3:
            try:
                # Use generate_content
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=selected_model,
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

                if response.candidates:
                    candidate = response.candidates[0]
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            from backend.utils.tool_schemas import validate_tool_call
                            from backend.utils.json_repair import repair_and_parse

                            # args can be a dict or a broken string
                            raw_args = fc.args
                            if isinstance(raw_args, str):
                                parsed_args, _ = repair_and_parse(raw_args)
                                raw_args = parsed_args or {}

                            raw_tc = {
                                "name": fc.name,
                                "params": raw_args if isinstance(raw_args, dict) else {}
                            }
                            validated = validate_tool_call(raw_tc)
                            if validated:
                                tool_call = validated.model_dump()

                        elif hasattr(part, "text") and part.text:
                            text_content += part.text

                # Also try to parse tool call from text (Gemini sometimes does this)
                if tool_call is None and text_content.strip():
                    from backend.utils.json_repair import repair_and_parse
                    from backend.utils.tool_schemas import validate_tool_call
                    parsed, _ = repair_and_parse(text_content)
                    if parsed and isinstance(parsed, dict):
                        if "tool_call" in parsed:
                            validated = validate_tool_call(parsed["tool_call"])
                            if validated:
                                tool_call = validated.model_dump()
                                text_content = ""

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

    async def generate_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
        model_override: Optional[str] = None,
    ) -> str:
        """
        Lightweight generation without tool-calling.
        Supports text-only and vision (text + image) requests.
        Used by Prompt Enhancer and Vision Critic.
        """
        model = model_override or self.model_name
        parts = []

        if image_bytes:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))

        parts.append(types.Part(text=prompt))

        contents = [types.Content(role="user", parts=parts)]

        retries = 0
        backoff = 2
        while retries < 3:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                if response.candidates and response.candidates[0].content.parts:
                    return "".join(
                        p.text for p in response.candidates[0].content.parts if p.text
                    )
                return ""
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "503" in err_msg or "quota" in err_msg:
                    logger.warning(f"Gemini simple call rate-limited. Retry in {backoff}s…")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                else:
                    raise
        raise RateLimitExceeded("Gemini Rate Limit exceeded (generate_simple)")

    async def generate_stream(
        self,
        messages: list,
        tools: list = None,
        on_token=None,
        task_hint: str = "default",
        **kwargs
    ) -> dict:
        """True streaming from Gemini API."""
        import google.generativeai as genai
        
        full_text = ""
        
        try:
            genai.configure(api_key=self.client.api_key)
            model_name = "gemini-1.5-flash" if task_hint in ("quick", "default") else "gemini-1.5-pro"
            model = genai.GenerativeModel(model_name)
            
            # Simple message format for genai directly
            formatted = []
            for msg in messages:
                if msg["role"] == "system":
                    continue
                role = "user" if msg["role"] in ["user", "tool"] else "model"
                formatted.append({"role": role, "parts": [msg.get("content", "")]})
            
            response = await asyncio.to_thread(
                model.generate_content,
                formatted,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,
                    temperature=0.7
                )
            )
            
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    if on_token:
                        await on_token({"type": "token", "content": chunk.text})
            
            return {"text": full_text, "tool_call": None, "model_used": model_name}
            
        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            return await self.generate_with_tools(messages, tools=tools)

    async def generate_with_image(
        self,
        prompt: str,
        image_base64: str,
        image_mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Multimodal generation: send image + text prompt to Gemini Flash Vision.
        Used by VisionFeedbackLoop for visual QA of generated content.
        """
        try:
            import google.generativeai as genai
            from PIL import Image
            import io
            import base64

            genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
            model = genai.GenerativeModel("gemini-1.5-flash")

            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))

            response = model.generate_content(
                [prompt, image],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )

            return {
                "text": response.text,
                "model_used": "gemini-1.5-flash-vision",
            }
        except ImportError as e:
            logger.warning(f"Vision deps missing: {e}")
            return {"text": "{}", "model_used": "none", "error": str(e)}
        except Exception as e:
            logger.error(f"Vision generation failed: {e}")
            return {"text": "{}", "model_used": "none", "error": str(e)}
