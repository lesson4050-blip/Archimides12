import asyncio
import websockets
import json
import uuid

async def main():
    sid = str(uuid.uuid4())
    uri = f"ws://localhost:8001/ws/{sid}"
    print(f"Connecting with session {sid}...")
    
    ws = await websockets.connect(uri, max_size=10*1024*1024)
    
    # Wait for session_ready
    resp = await ws.recv()
    print(f"Server: {resp}")
    
    task_msg = json.dumps({
        "task": "Найди актуальную информацию об Иране: политическая ситуация, экономика и международные отношения. Составь краткий, но информативный отчет."
    }, ensure_ascii=False)
    
    await ws.send(task_msg)
    print("Task sent! Collecting results into iran_report.md...\n")
    
    report_file = "iran_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Отчет по Ирану\n\n")
    
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=600)
            data = json.loads(msg)
            t = data.get("type", "")
            
            if t == "thought":
                print(f"[THOUGHT] Processing...")
            elif t == "tool_call":
                tool_name = data.get("tool")
                print(f"[TOOL] Using {tool_name}")
                if tool_name == "message":
                    content = data.get("params", {}).get("message") or data.get("params", {}).get("content")
                    if content:
                        print(f"\n[RECEIVED REPORT] Saving to {report_file}...")
                        with open(report_file, "a", encoding="utf-8") as f:
                            f.write(content)
                        print("Done!")
            elif t in ["final_answer", "agent_response", "message_info"]:
                content = data.get("message", data.get("answer", data.get("content", data.get("text", ""))))
                if content:
                    print(f"\n[RECEIVED REPORT] Saving to {report_file}...")
                    with open(report_file, "a", encoding="utf-8") as f:
                        f.write(content)
                    print("Done!")
                if t == "final_answer": break
            elif t == "agent_done":
                break
            elif t == "agent_error":
                print(f"[ERROR] {data.get('message', '')}")
                break
    except Exception as e:
        print(f"Finished: {e}")
    finally:
        await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
