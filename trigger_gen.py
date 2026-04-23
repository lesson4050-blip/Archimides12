import httpx
import asyncio
import json

async def trigger():
    url = "http://127.0.0.1:8000/api/v1/ppt/presentation/generate/async"
    payload = {
        "content": "Archimedes: The Dawn of Sovereign AI Agents. How agentic systems are reshaping the digital landscape.",
        "instructions": "Create a high-end, premium presentation. Use the midnight_obsidian theme. Focus on technical excellence and future-proof architecture.",
        "tone": "professional",
        "verbosity": "standard",
        "n_slides": 6,
        "language": "English",
        "export_as": "pptx"
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(trigger())
