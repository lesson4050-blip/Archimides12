from datetime import datetime
from typing import Optional

from enums.llm_provider import LLMProvider
from models.llm_message import LLMSystemMessage, LLMUserMessage
from models.llm_tools import SearchWebTool
from services.llm_client import LLMClient
from utils.get_dynamic_models import get_presentation_outline_model_with_n_slides
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_provider import get_model


def get_system_prompt(
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    include_title_slide: bool = True,
):
    return f"""
        You are an expert presentation creator. Generate structured presentations with massive professional depth. 
        Stop generating generic 3-sentence slides. For a major company or complex topic, provide deep analysis, names (CEO, founders), history, and specific metrics.

        Try to use available tools (Search Web) for the most accurate and recent data.

        {"# User Instruction:" if instructions else ""}
        {instructions or ""}

        # Requirements:
        - Provide content for each slide as PLAIN TEXT (No markdown, no **, no #, no bullet lists in text).
        - Each slide should have 5-7 distinct points of high-quality info.
        - Maximum 200 characters per point for English, 120 for Russian.
        - Place massive emphasis on numerical data, dates, and specific names.
        - Logical flow is mandatory.
        - No images in content.
        - Each point must be a complete, professional sentence.
        - Search web is REQUIRED for current company profiles.
        
        {"- Always make first slide a title slide." if include_title_slide else "- Do not include title slide."}
        - Do not generate table of contents.
    """


def get_user_prompt(
    content: str,
    n_slides: int,
    language: str,
    additional_context: Optional[str] = None,
):
    return f"""
        **Input:**
        - User provided content: {content or "Create presentation"}
        - Output Language: {language}
        - Number of Slides: {n_slides}
        - Current Date and Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        - Additional Information: {additional_context or ""}
    """


def get_messages(
    content: str,
    n_slides: int,
    language: str,
    additional_context: Optional[str] = None,
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    include_title_slide: bool = True,
):
    return [
        LLMSystemMessage(
            content=get_system_prompt(
                tone, verbosity, instructions, include_title_slide
            ),
        ),
        LLMUserMessage(
            content=get_user_prompt(content, n_slides, language, additional_context),
        ),
    ]


async def generate_ppt_outline(
    content: str,
    n_slides: int,
    language: Optional[str] = None,
    additional_context: Optional[str] = None,
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    include_title_slide: bool = True,
    web_search: bool = False,
):
    model = get_model()
    response_model = get_presentation_outline_model_with_n_slides(n_slides)

    client = LLMClient()
    providers_with_search_tool = {
        LLMProvider.OPENAI,
        LLMProvider.ANTHROPIC,
        LLMProvider.GOOGLE,
    }
    use_search_tool = (
        web_search
        and client.enable_web_grounding()
        and client.llm_provider in providers_with_search_tool
    )

    try:
        async for chunk in client.stream_structured(
            model,
            get_messages(
                content,
                n_slides,
                language,
                additional_context,
                tone,
                verbosity,
                instructions,
                include_title_slide,
            ),
            response_model.model_json_schema(),
            strict=True,
            tools=([SearchWebTool] if use_search_tool else None),
        ):
            yield chunk
    except Exception as e:
        yield handle_llm_client_exceptions(e)
