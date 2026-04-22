from typing import Optional
from pydantic import BaseModel, Field
from models.llm_message import LLMSystemMessage, LLMUserMessage
from services.llm_client import LLMClient
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_provider import get_model
from utils.safe_log import DEEP_LOGGER

class VisualPersonaModel(BaseModel):
    theme_category: str = Field(
        description="The aesthetic category (e.g., 'Modern Tech', 'Academic Strict', 'Creative Portfolio', 'Industrial Brutalism', 'Minimalist Elegance')"
    )
    curated_palette: str = Field(
        description="Select ONE curated palette name based on the theme: 'midnight_glass', 'cyber_neon', 'clean_editorial', 'warm_minimal', 'slate_professional'"
    )
    image_style: str = Field(
        description="Guidance for Pexels image search style to ensure cohesion (e.g., '3d abstract render', 'high contrast macro photography', 'minimalist architecture', 'cinematic product shot')"
    )
    typography_mood: str = Field(
        description="The mood of the fonts (e.g., 'sans-serif bold', 'classic serif', 'monospace technical')"
    )

def get_persona_messages(
    title: str,
    content: str,
    instructions: Optional[str] = None,
):
    return [
        LLMSystemMessage(
            content=f"""
                You are an elite Art Director and UI/UX Designer.
                Your task is to analyze the presentation context and define a "Visual Persona".
                
                # Style Guidelines:
                - For high-end professional, academic, or corporate topics, prefer 'clean_editorial' (light) to ensure maximum readability and a premium "agency" feel.
                - Only use 'midnight_glass' or 'cyber_neon' if the topic is explicitly about futuristic technology, AI, gaming, or night-life.
                - Avoid generic corporate styles; aim for a "Gemma/Gamma.app" premium aesthetic.

                # Curated Palettes available:
                - 'clean_editorial': Pure white background, high contrast black text, elegant spacing (The default for professional depth).
                - 'midnight_glass': Deep dark blues/blacks with vibrant glassmorphism (Use for AI/Future Tech).
                - 'slate_professional': Light gray backgrounds with deep navy accents (Traditional but modern).
                - 'warm_minimal': Cream/beige backgrounds, very soft and human.

                User Instructions (prioritize these): {instructions or "None"}
            """
        ),
        LLMUserMessage(
            content=f"Title: {title}\n\nContent/Topic Summary:\n{content[:1000]}",
        ),
    ]

async def define_visual_persona(
    title: str,
    content: str,
    instructions: Optional[str] = None,
) -> VisualPersonaModel:
    client = LLMClient()
    model = get_model()

    print(f"DEBUG: Brainstorming Visual Persona for: {title}")
    DEEP_LOGGER.log(f"Brainstorming Visual Persona for: {title}")

    try:
        response = await client.generate_structured(
            model=model,
            messages=get_persona_messages(title, content, instructions),
            response_format=VisualPersonaModel.model_json_schema(),
            strict=True,
        )
        
        persona = VisualPersonaModel(**response)
        print(f"DEBUG: Decided Persona: {persona.theme_category} | Palette: {persona.curated_palette}")
        DEEP_LOGGER.log(f"Decided Persona: {persona.theme_category} | Palette: {persona.curated_palette}")
        return persona
    except Exception as e:
        DEEP_LOGGER.log_error("Failed to define Visual Persona, falling back to clean_editorial", e)
        # Fallback to a safe, default persona
        return VisualPersonaModel(
            theme_category="Safe Default",
            curated_palette="slate_professional",
            image_style="high quality professional photography",
            typography_mood="sans-serif clean"
        )
