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

class SlideLayoutSelectionModel(BaseModel):
    layout_index: int = Field(description="The index of the selected layout for the slide")

def get_slide_selection_messages(
    presentation_layout: PresentationLayoutModel,
    slide_content: str,
    slide_index: int,
    total_slides: int,
    instructions: Optional[str] = None,
):
    return [
        LLMSystemMessage(
            content=f"""
                You're a professional presentation designer. Your task is to select the most appropriate slide layout for slide {slide_index + 1} of {total_slides}.

                {presentation_layout.to_string()}

                # Layout Selection Guidelines
                1. Match layout to content purpose:
                   - Opening/Title -> Look for title layouts
                   - Content/Lists -> Balanced layouts
                   - Visuals/Media -> Image focused layouts
                2. Instructions: {instructions or "Follow standard design principles."}

                Return the index of the best matching layout for the provided slide content.
            """,
        ),
        LLMUserMessage(
            content=f"Slide Content:\n{slide_content}",
        ),
    ]

async def generate_presentation_structure(
    presentation_outline: PresentationOutlineModel,
    presentation_layout: PresentationLayoutModel,
    instructions: Optional[str] = None,
    using_slides_markdown: bool = False,
) -> PresentationStructureModel:

    client = LLMClient()
    model = get_model()
    n_slides = len(presentation_outline.slides)
    selected_layouts: List[int] = []

    DEEP_LOGGER.log(f"Starting iterative layout selection for {n_slides} slides")

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
                    instructions
                ),
                response_format=SlideLayoutSelectionModel.model_json_schema(),
                strict=True,
            )
            layout_index = response.get("layout_index", 0)
            
            # Validation: ensure layout_index is within bounds
            if layout_index < 0 or layout_index >= len(presentation_layout.slides):
                DEEP_LOGGER.log(f"Warning: Model returned out of bounds index {layout_index}, defaulting to 0", "WARNING")
                layout_index = 0
                
            selected_layouts.append(layout_index)
            DEEP_LOGGER.log(f"Selected layout index {layout_index} for slide {i+1}")
            
        except Exception as e:
            DEEP_LOGGER.log_error(f"Failed to select layout for slide {i+1}, defaulting to 0", e)
            selected_layouts.append(0)

    return PresentationStructureModel(slides=selected_layouts)
