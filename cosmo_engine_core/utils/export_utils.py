from models.pptx_models import (
    PptxPresentationModel, PptxSlideModel, PptxTextBoxModel, 
    PptxPositionModel, PptxParagraphModel, PptxTextRunModel,
    PptxPictureBoxModel, PptxPictureModel
)
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from models.presentation_and_path import PresentationAndPath
from typing import List, Literal
from services.pptx_presentation_creator import PptxPresentationCreator
from services.temp_file_service import TEMP_FILE_SERVICE
from utils.asset_directory_utils import get_exports_directory
from pathvalidate import sanitize_filename
import os
import uuid


async def export_presentation(
    presentation: PresentationModel, slides: List[SlideModel], export_as: Literal["pptx", "pdf"]
) -> PresentationAndPath:
    if export_as == "pptx":
        # Local conversion logic: DB Models -> PptxPresentationModel
        pptx_slides = []
        for slide in slides:
            shapes = []
            content = slide.content or {}
            
            # Simple heuristic mapping for our mocked templates
            # Title Slide
            if "title" in content:
                shapes.append(PptxTextBoxModel(
                    position=PptxPositionModel(left=100, top=200, width=1080, height=100),
                    paragraphs=[PptxParagraphModel(text=content.get("title", ""), font_weight=700)]
                ))
                if "subtitle" in content:
                    shapes.append(PptxTextBoxModel(
                        position=PptxPositionModel(left=100, top=320, width=1080, height=100),
                        paragraphs=[PptxParagraphModel(text=content.get("subtitle", ""))]
                    ))
            
            # Content Slide
            elif "heading" in content:
                shapes.append(PptxTextBoxModel(
                    position=PptxPositionModel(left=50, top=50, width=1180, height=80),
                    paragraphs=[PptxParagraphModel(text=content.get("heading", ""), font_weight=700)]
                ))
                
                bullets = content.get("bullet_points", [])
                paragraphs = []
                for b in bullets:
                    paragraphs.append(PptxParagraphModel(text=f"• {b}"))
                
                shapes.append(PptxTextBoxModel(
                    position=PptxPositionModel(left=50, top=150, width=1180, height=500),
                    paragraphs=paragraphs
                ))
            
            # Handle images if present in content
            if "image" in content and content["image"]:
                shapes.append(PptxPictureBoxModel(
                    position=PptxPositionModel(left=800, top=150, width=400, height=300),
                    picture=PptxPictureModel(is_network=False, path=content["image"])
                ))

            pptx_slides.append(PptxSlideModel(
                note=slide.speaker_note,
                shapes=shapes
            ))

        pptx_model = PptxPresentationModel(
            name=presentation.title or "Presentation",
            slides=pptx_slides
        )

        # Create PPTX file
        temp_dir = TEMP_FILE_SERVICE.create_temp_dir()
        pptx_creator = PptxPresentationCreator(pptx_model, temp_dir)
        await pptx_creator.create_ppt()

        export_directory = get_exports_directory()
        title = presentation.title or str(uuid.uuid4())
        pptx_path = os.path.join(
            export_directory,
            f"{sanitize_filename(title)}.pptx",
        )
        pptx_creator.save(pptx_path)

        return PresentationAndPath(
            presentation_id=presentation.id,
            path=pptx_path,
        )
    else:
        # PDF export fallback (simplified)
        return PresentationAndPath(
            presentation_id=presentation.id,
            path="PDF_EXPORT_NOT_IMPLEMENTED_LOCALLY.pdf"
        )
