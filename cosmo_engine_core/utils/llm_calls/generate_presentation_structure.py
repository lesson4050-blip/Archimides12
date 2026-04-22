from typing import List, Optional
from pydantic import BaseModel, Field
from models.llm_message import LLMSystemMessage, LLMUserMessage
from models.presentation_layout import PresentationLayoutModel
from models.presentation_outline_model import PresentationOutlineModel
from services.llm_client import LLMClient
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_provider import get_model
from models.presentation_structure_model import PresentationStructureModel
from utils.safe_log import DEEP_LOGGER

from utils.llm_calls.define_visual_persona import VisualPersonaModel

class SlideLayoutSelectionModel(BaseModel):
    layout_index: int = Field(description="The index of the selected layout for the slide")
    rationale: str = Field(description="Briefly explain why this layout fits the Visual Persona and content purpose")

def get_slide_selection_messages(
    presentation_layout: PresentationLayoutModel,
    slide_content: str,
    slide_index: int,
    total_slides: int,
    visual_persona: Optional[VisualPersonaModel] = None,
    instructions: Optional[str] = None,
):
    persona_context = ""
    if visual_persona:
        persona_context = f"""
        # Visual Persona Context
        - Theme Category: {visual_persona.theme_category}
        - Typography Mood: {visual_persona.typography_mood}
        - Aesthetic Goal: Match the vibe of '{visual_persona.curated_palette}' palette.
        """

    return [
        LLMSystemMessage(
            content=f"""
                You're a professional Art Director and Presentation Designer. 
                Your task is to select the most appropriate slide layout for slide {slide_index + 1} of {total_slides}.
                
                {persona_context}

                # Available Layouts
                {presentation_layout.to_string()}

                # Layout Selection & Visual Rhythm Guidelines
                1. Match layout to content purpose:
                   - Opening/Title -> Look for title layouts.
                   - Content/Lists -> Balanced layouts.
                   - Visuals/Media -> Image focused layouts.
                2. **Visual Rhythm**: Avoid using the same layout index multiple times in a row. 
                3. **Alternation**: If the content allows, alternate between left-aligned and right-aligned layouts to create kinetic energy.
                4. **Persona Alignment**: If the Persona is 'Scientific', prefer clear, data-focused grids. If 'Creative', prefer asymmetrical or bold layouts.
                5. Instructions: {instructions or "Follow standard high-end design principles."}

                Return the index of the best matching layout and a brief rationale.
            """,
        ),
        LLMUserMessage(
            content=f"Slide Content:\n{slide_content}",
        ),
    ]

async def generate_presentation_structure(
    presentation_outline: PresentationOutlineModel,
    presentation_layout: PresentationLayoutModel,
    visual_persona: Optional[VisualPersonaModel] = None,
    instructions: Optional[str] = None,
    using_slides_markdown: bool = False,
) -> PresentationStructureModel:

    client = LLMClient()
    model = get_model()
    n_slides = len(presentation_outline.slides)
    selected_layouts: List[int] = []

    DEEP_LOGGER.log(f"Starting iterative layout selection for {n_slides} slides with persona: {visual_persona.theme_category if visual_persona else 'None'}")

    for i, slide in enumerate(presentation_outline.slides):
        DEEP_LOGGER.log(f"Selecting layout for slide {i+1}/{n_slides}")
        try:
            response = await client.generate_structured(
                model=model,
                messages=get_slide_selection_messages(
                    presentation_layout,
                    slide.content,
                    i,
                    n_slides,
                    visual_persona,
                    instructions
                ),
                response_format=SlideLayoutSelectionModel.model_json_schema(),
                strict=True,
            )
            layout_index = response.get("layout_index", 0)
            rationale = response.get("rationale", "No rationale")
            
            DEEP_LOGGER.log(f"Selected layout index {layout_index} for slide {i+1}. Rationale: {rationale}")
            
            # Validation: ensure layout_index is within bounds
            if layout_index < 0 or layout_index >= len(presentation_layout.slides):
                DEEP_LOGGER.log(f"Warning: Model returned out of bounds index {layout_index}, defaulting to 0", "WARNING")
                layout_index = 0
                
            selected_layouts.append(layout_index)
            
        except Exception as e:
            DEEP_LOGGER.log_error(f"Failed to select layout for slide {i+1}, defaulting to 0", e)
            selected_layouts.append(0)

    return PresentationStructureModel(slides=selected_layouts)
