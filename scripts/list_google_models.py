import asyncio
from google import genai
from backend.config import settings

async def list_models():
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    print("--- Available Google Models ---")
    try:
        # Note: genai.Client.models.list() returns an iterator or list
        # We need to see what models are actually there
        for m in client.models.list():
            print(f"Model: {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
