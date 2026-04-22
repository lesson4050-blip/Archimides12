from datetime import datetime
from typing import Optional
from models.llm_message import LLMSystemMessage, LLMUserMessage
from models.presentation_layout import SlideLayoutModel
from models.presentation_outline_model import SlideOutlineModel
from services.llm_client import LLMClient
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_provider import get_model
from utils.schema_utils import add_field_in_schema, remove_fields_from_schema


def get_system_prompt(
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
):
    return f"""
        Generate structured slide based on provided outline, follow mentioned steps and notes and provide structured output.

        {"# User Instructions:" if instructions else ""}
        {instructions or ""}

        {"# Tone:" if tone else ""}
        {tone or ""}

        {"# Verbosity:" if verbosity else ""}
        {verbosity or ""}

        # Steps
        1. Analyze the outline.
        2. Generate structured slide based on the outline.
        3. IMPORTANT: Distribute the information across ALL available fields in the schema (e.g., bullets, metrics, chartData).
        4. If a field like "description" has a small character limit (e.g. 300), put the additional detail into "bullets" or other list fields.
        5. Generate speaker note that is simple, clear, concise and to the point.

        # Visual Excellence (Gamma/Kimi Quality)
        - If the schema contains an `image` object, you MUST provide a detailed, artistic `__image_prompt__`.
        - Image prompts should be cinematic, professional, or corporate-editorial (e.g., "Cinematic shot of NVIDIA H100 GPU in a high-tech data center, neon blue lighting, hyper-realistic").
        - If the schema contains `icons`, provide precise `__icon_query__` terms (e.g., "artificial intelligence", "database", "revenue growth").

        # Notes
        - Slide body should not use words like "This slide", "This presentation".
        - Rephrase the slide body to make it flow naturally.
        - DO NOT USE ANY MARKDOWN FORMATTING (no **, _, etc). Output only plain text.
        - Strictly follow the max and min character limit for every property in the slide.
        - Never go over the max character limit.
        - If you have more content than fits in a field, MOVE IT to another appropriate field (like a bullet list or metric) instead of truncating.
        - For Metrics: Extract numerical data points from the outline into the `metrics` or `metricCards` array.
        - For Charts: If data is available, populate `chartData`.

        Provide output in json format and **don't include <parameters> tags**.

        # Image and Icon Output Format
        image: {{
            __image_prompt__: string,
        }}
        icon: {{
            __icon_query__: string,
        }}

    """


def get_user_prompt(outline: str, language: str):
    return f"""
        ## Current Date and Time
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        ## Icon Query And Image Prompt Language
        English

        ## Slide Content Language
        {language}

        ## Slide Outline
        {outline}
    """


def get_messages(
    outline: str,
    language: str,
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
):

    return [
        LLMSystemMessage(
            content=get_system_prompt(tone, verbosity, instructions),
        ),
        LLMUserMessage(
            content=get_user_prompt(outline, language),
        ),
    ]


async def get_slide_content_from_type_and_outline(
    slide_layout: SlideLayoutModel,
    outline: SlideOutlineModel,
    language: str,
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
):
    client = LLMClient()
    model = get_model()

    response_schema = remove_fields_from_schema(
        slide_layout.json_schema, ["__image_url__", "__icon_url__"]
    )
    response_schema = add_field_in_schema(
        response_schema,
        {
            "__speaker_note__": {
                "type": "string",
                "minLength": 100,
                "maxLength": 250,
                "description": "Speaker note for the slide",
            }
        },
        True,
    )

    messages = get_messages(
        outline.content,
        language,
        tone,
        verbosity,
        instructions,
    )
    print(
        f"get_slide_content_from_type_and_outline: model={model} outline_len={len(outline.content or '')} language={language}"
    )
    try:
        response = await client.generate_structured(
            model=model,
            messages=messages,
            response_format=response_schema,
            strict=False,
        )
        print(
            f"get_slide_content_from_type_and_outline: response is None={response is None} keys={list(response.keys())[:6] if isinstance(response, dict) else None}"
        )
        return response

    except Exception as e:
        print(f"get_slide_content_from_type_and_outline: exception={e}")
        raise handle_llm_client_exceptions(e)
