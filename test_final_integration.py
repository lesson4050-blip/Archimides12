import asyncio
import websockets
import json
import uuid

async def test_agent():
    session_id = f"test-final-{uuid.uuid4().hex[:6]}"
    uri = f"ws://localhost:8001/ws/{session_id}"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # Wait for ready
            resp = await websocket.recv()
            print(f"Server: {resp}")
            
            # Send task
            task = {
                "type": "task",
                "agent_id": "researcher",
                "task": "Research CrewAI framework and write a short summary to crewai.md."
            }
            await websocket.send(json.dumps(task))
            print("Task Sent.")
            
            # Listen for 60 seconds
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 60:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(msg)
                    t = data.get("type")
                    content = data.get("content", data.get("text", ""))
                    
                    if t == "thought":
                        print(f"THOUGHT: {content}")
                    elif t == "message_info":
                        print(f"INFO: {content}")
                    elif t == "artifact":
                        print(f"ARTIFACT CREATED: {data.get('name')}")
                    elif t == "message_result":
                        print(f"RESULT: {content}")
                        break
                except asyncio.TimeoutError:
                    continue
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent())
