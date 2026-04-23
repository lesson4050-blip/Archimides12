import json
import os
import aiohttp
from typing import Literal, List
import uuid
from fastapi import HTTPException
from pathvalidate import sanitize_filename

from models.presentation_and_path import PresentationAndPath
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from services.direct_pptx_builder import DirectPptxBuilder
from services.pptx_themes import guess_theme
from services.temp_file_service import TEMP_FILE_SERVICE
from utils.asset_directory_utils import get_exports_directory


async def export_presentation(
    presentation: PresentationModel, slides: List[SlideModel], export_as: Literal["pptx", "pdf"]
) -> PresentationAndPath:
    if export_as == "pptx":
        # Build slide data from the database models
        slides_data = []
        for slide in slides:
            slide_content = {}
            if hasattr(slide, 'content') and slide.content:
                if isinstance(slide.content, str):
                    try:
                        slide_content = json.loads(slide.content)
                    except json.JSONDecodeError:
                        slide_content = {"title": slide.content}
                else:
                    slide_content = slide.content
            
            slide_entry = {
                "content": slide_content,
                "slideType": getattr(slide, 'slide_type', '') or getattr(slide, 'layout', '') or '',
                "speakerNotes": getattr(slide, 'speaker_notes', '') or '',
            }
            slides_data.append(slide_entry)

        # Pick theme based on presentation title
        title = presentation.title or ""
        theme = guess_theme(title)

        # Build PPTX using DirectPptxBuilder
        builder = DirectPptxBuilder(theme=theme)
        await builder.build(slides_data, title=title)

        # Save
        export_directory = get_exports_directory()
        safe_title = sanitize_filename(title or str(uuid.uuid4()))
        pptx_path = os.path.join(export_directory, f"{safe_title}.pptx")
        builder.save(pptx_path)

        return PresentationAndPath(
            presentation_id=presentation.id,
            path=pptx_path,
        )
    else:
        # PDF export: still uses Artist for now
        async with aiohttp.ClientSession() as session:
            artist_url = os.environ.get("ARTIST_URL", "http://localhost:3005")
            async with session.post(
                f"{artist_url}/api/export-as-pdf",
                json={
                    "id": str(presentation.id),
                    "title": sanitize_filename(presentation.title or str(uuid.uuid4())),
                },
            ) as response:
                response_json = await response.json()

        return PresentationAndPath(
            presentation_id=presentation.id,
            path=response_json.get("path") or "",
        )
