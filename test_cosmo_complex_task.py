import asyncio
import websockets
import json
import uuid

async def main():
    sid = f"test-complex-{uuid.uuid4().hex[:6]}"
    uri = f"ws://localhost:8001/ws/{sid}"
    print(f"Connecting to Archimedes COSMO (Session: {sid})...")
    
    try:
        async with websockets.connect(uri) as ws:
            # 1. Wait for session ready
            resp = await ws.recv()
            print(f"Server Response: {resp}")
            
            # 2. Send Complex Task
            task_text = (
                "Research 3 popular AI Agent frameworks (CrewAI, LangGraph, AutoGPT). "
                "Compare their key features in a Markdown table. "
                "Save the report to 'ai_frameworks.md' in the workspace. "
                "Then verify the file exists using shell."
            )
            task = {
                "type": "task",
                "agent_id": "researcher",
                "task": task_text
            }
            await ws.send(json.dumps(task))
            print(f"Task Sent: {task_text}")
            
            # 3. Monitor Events
            print("\n--- Event Stream ---\n")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=300)
                    event = json.loads(msg)
                    etype = event.get("type")
                    
                    if etype == "thought":
                        print(f"THOUGHT: {event.get('content')}")
                    elif etype == "message_info":
                        print(f"INFO: {event.get('content')}")
                    elif etype == "tool_call":
                        print(f"TOOL CALL: {event.get('tool')} ({json.dumps(event.get('params'))})")
                    elif etype == "tool_result":
                        print(f"TOOL RESULT: {str(event.get('content'))[:200]}...")
                    elif etype == "artifact":
                        print(f"ARTIFACT: {event.get('name')} ({event.get('language')})")
                        print(f"--- Content (Preview) ---\n{event.get('content')[:500]}\n---")
                    elif etype == "message_result":
                        print(f"\nFINAL RESULT:\n{event.get('content')}")
                        break
                    elif etype == "agent_error":
                        print(f"ERROR: {event.get('content')}")
                        break
                    else:
                        print(f"EVENT {etype}: {msg[:200]}...")
                        
                except asyncio.TimeoutError:
                    print("Timeout: No events for 5 minutes.")
                    break
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
