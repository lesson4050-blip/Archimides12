import asyncio
import websockets
import json
import uuid
import sys

async def test(task_text):
    session_id = f"manual_{uuid.uuid4().hex[:4]}"
    uri = f"ws://127.0.0.1:8001/ws/{session_id}"
    print(f"\n--- TASK: {task_text} ---")
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"task": task_text}))
            async for msg in ws:
                # Raw print each event for the user
                print(msg)
                data = json.loads(msg)
                
                # Stop on result or error
                if data.get("type") == "tool_call" and data["tool"] == "message" and data["params"].get("type") == "result":
                    print("\n[SUCCESS] Result received.")
                    break
                if data.get("type") == "agent_error":
                    print(f"\n[ERROR] {data.get('message')}")
                    break
                if data.get("type") == "session_end":
                    print(f"\n[END] Reason: {data.get('reason')}")
                    break
    except Exception as e:
        print(f"\n[CONNECTION ERROR] {e}")

if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    asyncio.run(test(task))
