import httpx
import asyncio
import json

async def trigger():
    url = "http://127.0.0.1:8000/api/v1/ppt/presentation/generate/async"
    payload = {
        "content": "Биология: История возникновения жизни и становление науки. От первых микроорганизмов до сложных экосистем.",
        "instructions": "Создай высококачественную презентацию. Используй новый премиальный дизайн COSMO с анимациями GSAP. Язык презентации: Русский.",
        "tone": "educational",
        "verbosity": "standard",
        "n_slides": 8,
        "language": "Russian",
        "export_as": "pptx"
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
