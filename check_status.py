import httpx
import asyncio
import sys

async def check(task_id):
    url = f"http://127.0.0.1:8000/api/v1/ppt/presentation/status/{task_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        print(response.json())

if __name__ == "__main__":
    asyncio.run(check(sys.argv[1]))
