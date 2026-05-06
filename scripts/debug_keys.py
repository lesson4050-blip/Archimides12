import os
import asyncio
from dotenv import load_dotenv
import httpx

load_dotenv()

async def test_groq():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("Groq: No key found")
        return
    print(f"Groq: Testing key {key[:10]}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "hi"}]
                },
                timeout=10
            )
            if resp.status_code == 200:
                print("Groq: OK")
            else:
                print(f"Groq: Error {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Groq: Exception {e}")

async def test_gemini():
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("Gemini: No key found")
        return
    print(f"Gemini: Testing key {key[:10]}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": "hi"}]}]},
                timeout=10
            )
            if resp.status_code == 200:
                print("Gemini: OK")
            else:
                print(f"Gemini: Error {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Gemini: Exception {e}")

async def main():
    await test_groq()
    print("-" * 20)
    await test_gemini()

if __name__ == "__main__":
    asyncio.run(main())
