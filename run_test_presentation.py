import asyncio
import os

from backend.presentation.pipeline import PresentationPipeline
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    pipeline = PresentationPipeline()
    result = await pipeline.generate(
        prompt="Create a 5-slide pitch deck about Archimedes, his inventions, and why he is the father of engineering. Use a professional, historical tech theme.",
        theme="tech-blue",
        output_path="output/test_archimedes.pdf"
    )
    if hasattr(result, "pdf_path") and result.pdf_path:
        size = os.path.getsize(result.pdf_path) / 1024
        print(f"Generated: {result.pdf_path}, Size: {size:.1f} KB")
        if size > 80:
            print("SUCCESS: Size is > 80 KB.")
        else:
            print("WARNING: File size is smaller than expected.")
    else:
        print("Failed to generate PDF path.")

if __name__ == "__main__":
    asyncio.run(main())
