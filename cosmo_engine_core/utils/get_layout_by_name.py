import aiohttp
from fastapi import HTTPException
from models.presentation_layout import PresentationLayoutModel, SlideLayoutModel
from typing import List

async def get_layout_by_name(layout_name: str) -> PresentationLayoutModel:
    # Since the original NextJS frontend is removed, we mock the basic template schemas locally.
    title_schema = {
        "title": "Title Slide", "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Main title"},
            "subtitle": {"type": "string", "description": "Subtitle"}
        }, "required": ["title", "subtitle"]
    }
    content_schema = {
        "title": "Content Slide", "type": "object",
        "properties": {
            "heading": {"type": "string"},
            "bullet_points": {
                "type": "array", 
                "items": {"type": "string"}
            }
        }, "required": ["heading", "bullet_points"]
    }
    
    return PresentationLayoutModel(
        name=layout_name,
        ordered=False,
        slides=[
            SlideLayoutModel(id="title_slide", name="Title", description="Title slide", json_schema=title_schema),
            SlideLayoutModel(id="content_slide", name="Content", description="Content slide", json_schema=content_schema)
        ]
    )
