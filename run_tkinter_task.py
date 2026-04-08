import asyncio
import websockets
import json
import uuid

async def main():
    sid = str(uuid.uuid4())
    uri = f"ws://localhost:8001/ws/{sid}"
    print(f"Connecting to start test task: {sid}...")
    
    ws = await websockets.connect(uri, max_size=10*1024*1024)
    resp = await ws.recv()
    print(f"Server: {resp}")
    
    # We expect novnc_ready to be sent immediately after task submission
    task_msg = json.dumps({
        "task": "Напиши простую цифровую игру Змейка на Python с использованием библиотеки pygame. Сохрани в snake.py и запусти. Если pygame не установлен, установи его. Проверь работоспособность игры на экране."
    }, ensure_ascii=False)
    
    await ws.send(task_msg)
    print("Task sent!")
    
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=600)
            data = json.loads(msg)
            t = data.get("type", "")
            
            if t == "novnc_ready":
                print(f"[NOVNC READY] URL: {data.get('url')}")
                
            elif t == "plan_update":
                phases = data.get("phases", [])
                print(f"\n[PLAN UPDATE]")
                for i, p in enumerate(phases):
                    print(f"  {i+1}. {p.get('title')} - [{p.get('status')}]")
                    
            elif t == "thought":
                print(f"[THOUGHT] Processing... (iteration {data.get('iteration')})")
                
            elif t == "tool_call":
                print(f"[TOOL] Using {data.get('tool')}")
                
            elif t == "tool_result":
                success = data.get('success')
                print(f"[RESULT] {data.get('tool')} -> {'Success' if success else 'Failed'}")
                text = data.get("output", "")
                if len(text) > 200: text = text[:200] + "..."
                print(f"   Output: {text.strip()}")
                
            elif t in ["final_answer", "agent_response", "message_info"]:
                content = data.get("message", data.get("answer", data.get("content", data.get("text", ""))))
                if content:
                    print(f"\n[MESSAGE TO USER]\n{content}\n")
                if t == "final_answer": break
                
            elif t == "agent_done" or t == "session_end":
                print(f"[{t}] Finished.")
                break
                
            elif t == "agent_error":
                print(f"[ERROR] {data.get('message', '')}")
                break
                
    except Exception as e:
        print(f"Connection ended: {e}")
    finally:
        await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
