import asyncio
import websockets
import json
import uuid

async def main():
    sid = str(uuid.uuid4())
    uri = f"ws://localhost:8001/ws/{sid}"
    print(f"Connecting with session {sid}...")
    
    ws = await websockets.connect(uri, max_size=10*1024*1024)
    
    # Wait for session_ready or session_queued
    resp = await ws.recv()
    print(f"Server: {resp}")
    data = json.loads(resp)
    if data.get("type") == "session_queued":
        resp2 = await ws.recv()
        print(f"Server: {resp2}")
    
    # Send the task
    task_msg = json.dumps({
        "task": "Найди актуальную информацию об Иране: последние новости, политическая ситуация, экономика и международные отношения на сегодняшний день."
    }, ensure_ascii=False)
    
    await ws.send(task_msg)
    print("Task sent! Waiting for responses...\n")
    
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=600)
            data = json.loads(msg)
            t = data.get("type", "")
            
            # Pretty print based on type
            if t == "thought":
                print(f"[THOUGHT] {data.get('content', '')}")
            elif t == "tool_call":
                print(f"[TOOL] {data.get('tool', '')} -> {json.dumps(data.get('params', {}), ensure_ascii=False)}")
            elif t == "tool_result":
                output = data.get("output", "")
                print(f"[RESULT] Received output ({len(str(output))} chars)")
            elif t == "plan_update":
                print(f"[PLAN] Updated phases: {len(data.get('phases', []))}")
            elif t == "final_answer" or t == "agent_response":
                print(f"\n{'='*60}")
                print(f"[FINAL ANSWER]")
                print(data.get("message", data.get("answer", data.get("content", ""))))
                print(f"{'='*60}\n")
                if t == "final_answer": break
            elif t == "agent_done":
                print(f"[DONE] Agent finished.")
                break
            elif t == "agent_error":
                print(f"[ERROR] {data.get('message', '')}")
                break
            else:
                print(f"[{t}] {json.dumps(data, ensure_ascii=False)[:200]}...")
    except asyncio.TimeoutError:
        print("Timeout waiting for response (600s)")
    except Exception as e:
        print(f"Connection ended: {e}")
    finally:
        await ws.close()
        print("Connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
