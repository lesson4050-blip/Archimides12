from typing import Optional
from pydantic import BaseModel, Field
from models.llm_message import LLMSystemMessage, LLMUserMessage
from services.llm_client import LLMClient
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_provider import get_model
from utils.safe_log import DEEP_LOGGER

class VisualPersonaModel(BaseModel):
    theme_category: str = Field(
        description="The aesthetic category (e.g., 'Modern Tech', 'Luxury Editorial', 'Industrial Brutalism', 'Minimalist Elegance', 'Cyber Obsidian')"
    )
    curated_palette: str = Field(
        description="Select ONE curated palette name based on the theme: 'midnight_glass', 'midnight_obsidian', 'clean_editorial', 'warm_minimal', 'industrial_brutalist', 'arctic_minimal'"
    )
    image_style: str = Field(
        description="Guidance for Pexels image search style to ensure cohesion (e.g., '3d abstract obsidian render', 'cinematic architectural photography', 'high-fashion editorial shot', 'grainy industrial macro')"
    )
    typography_mood: str = Field(
        description="The mood of the fonts (e.g., 'aggressive sans-serif', 'refined elegant serif', 'industrial monospace')"
    )

def get_persona_messages(
    title: str,
    content: str,
    instructions: Optional[str] = None,
):
    return [
        LLMSystemMessage(
            content=f"""
                You are a World-Class Creative Director from a top-tier design agency (like Pentagram or Huge).
                Your task is to define a "Visual Persona" for a pitch deck that must LOOK EXPENSIVE and ELITE.
                
                # DESIGN PHILOSOPHY:
                - AVOID generic corporate blue.
                - EMBRACE "The New Luxury": high contrast, intentional negative space, and bold typography.
                - For high-stakes tech/AI/Finance: Use 'midnight_obsidian' (Black & Gold) or 'midnight_glass' (Deep Navy).
                - For Innovation/Architecture/Design: Use 'clean_editorial' (Pure White) or 'industrial_brutalist' (Raw & Bold).
                - For Health/Lifestyle/Nature: Use 'warm_minimal' (Beige/Cream) or 'arctic_minimal' (Ice Blue).

                # Curated Palettes:
                - 'midnight_obsidian': Pure Black background, Gold accents, White text. Ultimate luxury.
                - 'midnight_glass': Deepest Navy, Indigo glow, Frosted glass effects. High-end Tech.
                - 'clean_editorial': Pure white, Swiss typography, Black accents. Professional & Sharp.
                - 'industrial_brutalist': Dark gray/black, Safety Orange accents, Monospace fonts. Raw & Powerful.
                - 'arctic_minimal': Soft cool grays, Sky Blue accents, airy and fresh.
                - 'warm_minimal': Cream/Bone background, Deep Brown text. Human & Soft.

                # Image Direction:
                Be extremely specific. Instead of "business meeting", use "low-angle cinematic shot of a brutalist concrete building with sharp shadows".

                User Instructions (CRITICAL): {instructions or "None"}
            """
        ),
        LLMUserMessage(
            content=f"TITLE OF PRESENTATION: {title}\n\nCONTENT ANALYSIS:\n{content[:1500]}",
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
