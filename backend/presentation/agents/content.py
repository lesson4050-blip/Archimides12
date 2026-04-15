import json
from typing import Dict, Any

from backend.agent.llm_router import llm_router, OutputMode
from backend.presentation.schemas import SlidePlan, SlideContent

class ContentAgent:
    """
    Expands each plan item -> SlideContent with bullet limits (<=15 words),
    tone adaptation, layout_id selection, and asset_query.
    """

    async def generate_content(self, slide_plan: SlidePlan, global_context: str) -> SlideContent:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert presentation content writer."
                    "You will receive a slide plan (title and goal) and the overall context. "
                    "Your task is to generate the concrete content for ONE slide.\n\n"
                    "RULES:\n"
                    "1. Title must be concise and engaging (max 12 words).\n"
                    "2. Generate 3 to 5 bullets. Each bullet must be concise, max 15 words, "
                    "with zero fluff.\n"
                    "3. Add useful speaker notes.\n"
                    "4. Pick ONE layout_id from the following options based on the content type:\n"
                    "   - 'title-bullets' (standard list)\n"
                    "   - 'timeline' (chronological steps or history)\n"
                    "   - 'two-columns' (comparison or balanced information)\n"
                    "   - 'quote-full' (emphasized key point or quote)\n"
                    "   - 'chart-grid' (data metrics or multiple key topics)\n"
                    "5. Provide an 'asset_query' which is a semantic image search phrase (e.g. 'history architecture tech') to fetch a relevant background/side image. If no image is needed, return null.\n"
                    "\n"
                    "IMPORTANT: Output ONLY the populated JSON data object. DO NOT output the JSON schema, DO NOT output any explanation or 'Here is the schema' text. Just the final JSON object with values."
                )
            },
            {
                "role": "user",
                "content": f"Global Context: {global_context}\n\nTarget Slide Plan:\n{slide_plan.model_dump_json()}"
            }
        ]

        result = await llm_router.call(
            messages=messages,
            mode=OutputMode.STRICT_JSON,
            response_model=SlideContent,
            task_hint="think"
        )
        return result
