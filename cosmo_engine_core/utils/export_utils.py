import json
import os
import aiohttp
from typing import Literal, List
import uuid
from fastapi import HTTPException
from pathvalidate import sanitize_filename

from models.pptx_models import PptxPresentationModel
from models.presentation_and_path import PresentationAndPath
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from services.pptx_presentation_creator import PptxPresentationCreator
from services.temp_file_service import TEMP_FILE_SERVICE
from utils.asset_directory_utils import get_exports_directory


async def export_presentation(
    presentation: PresentationModel, slides: List[SlideModel], export_as: Literal["pptx", "pdf"]
) -> PresentationAndPath:
    if export_as == "pptx":

        # Get the converted PPTX model from the Next.js service (Artist)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://localhost:3005/api/presentation_to_pptx_model?id={presentation.id}"
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Failed to get PPTX model: {error_text}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to convert presentation to PPTX model",
                    )
                pptx_model_data = await response.json()

        # Create PPTX file using the converted model
        pptx_model = PptxPresentationModel(**pptx_model_data)
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
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:3005/api/export-as-pdf",
                json={
                    "id": str(presentation.id),
                    "title": sanitize_filename(presentation.title or str(uuid.uuid4())),
                },
            ) as response:
                response_json = await response.json()

        return PresentationAndPath(
            presentation_id=presentation.id,
            path=response_json["path"],
        )
