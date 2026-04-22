import aiohttp
from fastapi import HTTPException
from models.presentation_layout import PresentationLayoutModel
import typing
import os

from utils.safe_log import DEEP_LOGGER

async def get_layout_by_name(layout_name: str) -> PresentationLayoutModel:
    DEEP_LOGGER.log(f"Fetching layout: {layout_name}")
    async with aiohttp.ClientSession() as session:
        artist_url = os.environ.get("ARTIST_URL", "http://localhost:3005")
        try:
            async with session.get(
                f"{artist_url}/api/template?group={layout_name}"
            ) as response:
                if response.status != 200:
                    status_code = response.status
                    response_text = await response.text()
                    DEEP_LOGGER.log_error(f"Failed to get layout from nextjs: status={status_code}, body={response_text}")
                    raise HTTPException(
                        status_code=500, detail="Failed to get format templates"
                    )
                result = await response.json()
                DEEP_LOGGER.log(f"Successfully fetched layout: {layout_name}")
                return PresentationLayoutModel(**typing.cast(dict, result))
        except Exception as e:
            if not isinstance(e, HTTPException):
                DEEP_LOGGER.log_error(f"Error connecting to artist: {e}")
            raise e
