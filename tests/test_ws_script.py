import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8001/ws/test-session-123"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        print("Connected. Waiting for session ready...")
        response = await websocket.recv()
        print(f"Received: {response}")
        
        msg = {"type": "task", "task": "Create a simple HTML page with a countdown timer from 60 seconds. Save it to /home/ubuntu/workspace/timer.html and serve it on port 8080."}
        print(f"Sending: {msg}")
        await websocket.send(json.dumps(msg))
        
        # We expect a series of messages from the agent. Let's listen for up to 300 seconds
        print("Listening for messages from agent...")
        deadline = asyncio.get_running_loop().time() + 300
        while asyncio.get_running_loop().time() < deadline:
            try:
                reply = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Reply: {reply}")
                reply_data = json.loads(reply)
                if reply_data.get("type") in ["message_result", "session_end"]:
                    break
            except asyncio.TimeoutError:
                pass
        print("Test script finished.")

if __name__ == "__main__":
    asyncio.run(test_ws())
