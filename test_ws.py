import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8001/ws/session-test123"
    async with websockets.connect(uri) as websocket:
        # Wait for ready message
        ready = await websocket.recv()
        print(f"Received: {ready}")
        
        # Send task
        msg = json.dumps({"type": "task", "task": "привет"})
        print(f"Sending: {msg}")
        await websocket.send(msg)
        
        # Listen for responses
        try:
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"Received: {response}")
        except asyncio.TimeoutError:
            print("Timeout waiting for response")

asyncio.run(test_ws())
