from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class SlidePlan(BaseModel):
    title: str = Field(..., description="The title of the slide")
    goal: str = Field(..., description="The intended goal or message of this slide")

class PresentationPlan(BaseModel):
    title: str = Field(..., description="Main title of the presentation")
    slides: List[SlidePlan] = Field(..., description="List of planned slides in order")

class SlideContent(BaseModel):
    title: str = Field(..., description="The final, engaging title for the slide (max 12 words)")
    bullets: List[str] = Field(..., description="List of concise bullet points (max 15 words each)")
    speaker_notes: str = Field(..., description="Notes for the speaker for this slide")
    layout_id: str = Field(..., description="Selected layout ID (e.g., 'title-bullets', 'timeline', 'two-columns')")
    asset_query: Optional[str] = Field(None, description="Semantic search query for finding an appropriate image")

class Theme(BaseModel):
    theme_id: str
    colors: Dict[str, str] = Field(..., description="CSS variable color map, e.g., {'primary': '#336699'}")
    typography: Dict[str, str] = Field(..., description="CSS typography map")
    spacing: Dict[str, str] = Field(..., description="CSS spacing variables")

class RenderedSlide(BaseModel):
    html: str = Field(..., description="The generated HTML snippet for the slide")
    css_classes: List[str] = Field(..., description="List of CSS classes applied")
    assets: Dict[str, str] = Field(..., description="Resolved assets map (e.g., {'image1': 'https://...'})")

class TaskStatus(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "rendering", "done", "failed"]
    progress: float = 0.0
    result_url: Optional[str] = None
    error: Optional[str] = None
