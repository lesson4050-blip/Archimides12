import json
import logging
from enum import Enum
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel

from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class OutputMode(Enum):
    TEXT = "text"
    STRICT_JSON = "json"

class LLMRouter:
    def __init__(self):
        self.router = ModelRouter()

    async def call(
        self,
        messages: list[dict],
        mode: OutputMode = OutputMode.TEXT,
        response_model: Optional[Type[T]] = None,
        task_hint: str = "default",
        max_retries: int = 3
    ) -> Any:
        # If strict JSON, we instruct the model and append the schema
        if mode == OutputMode.STRICT_JSON and response_model:
            schema = response_model.model_json_schema()
            sys_msg = (
                f"\nYou must output strictly valid JSON matching this schema:\n"
                f"{json.dumps(schema)}\n"
                f"Do not include markdown blocks like ```json."
            )
            
            # append schema instruction to the last message if user, or add system message
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += sys_msg
            else:
                messages.insert(0, {"role": "system", "content": sys_msg})

        for attempt in range(max_retries):
            try:
                response = await self.router.generate(messages=messages, task_hint=task_hint)
                text = response.get("text", "")
                
                if mode == OutputMode.STRICT_JSON and response_model:
                    # Clean up common markdown formatting
                    text = text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    elif text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                    
                    decoder = json.JSONDecoder()
                    pos = 0
                    last_error = None
                    
                    # Search for any JSON object that validates against the model
                    while True:
                        start_idx = text.find("{", pos)
                        if start_idx == -1:
                            break
                        
                        try:
                            data, pos = decoder.raw_decode(text, start_idx)
                            # Attempt to validate
                            try:
                                return response_model(**data)
                            except Exception as ve:
                                last_error = ve
                                # Not this object, continue searching from the next character
                                pos = start_idx + 1
                                continue
                        except json.JSONDecodeError:
                            pos = start_idx + 1
                            continue
                    
                    if last_error:
                        raise last_error
                    raise ValueError("No valid JSON object matching the schema found in response")
                
                return text

            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e

llm_router = LLMRouter()
