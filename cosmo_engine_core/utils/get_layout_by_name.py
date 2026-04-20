import aiohttp
from fastapi import HTTPException
from models.presentation_layout import PresentationLayoutModel
import typing


async def get_layout_by_name(layout_name: str) -> PresentationLayoutModel:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://localhost:3005/api/template?group={layout_name}"
        ) as response:
            if response.status != 200:
                print(f"Failed to get layout from nextjs: {await response.text()}")
                raise HTTPException(
                    status_code=500, detail="Failed to get format templates"
                )
            result = await response.json()
            return PresentationLayoutModel(**typing.cast(dict, result))
