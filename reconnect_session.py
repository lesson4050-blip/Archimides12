import asyncio
import websockets
import json
import os

async def main():
    session_id = "139a5938-a7cc-446e-9d1e-efd4baeb7c60"
    uri = f"ws://localhost:8001/ws/{session_id}"
    print(f"Connecting to persistent session {session_id}...")
    
    try:
        async with websockets.connect(uri) as ws:
            print("Successfully connected. Listening for final response...")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(msg)
                    t = data.get("type")
                    
                    if t == "tool_call" and data.get("tool") == "message":
                        print("\n" + "="*60)
                        print("REPORT RECEIVED (via tool_call):")
                        content = data.get("params", {}).get("message") or data.get("params", {}).get("content")
                        print(content)
                        print("="*60 + "\n")
                        with open("iran_report_final.md", "w", encoding="utf-8") as f:
                            f.write(content)
                    
                    elif t in ["final_answer", "agent_response", "message_info"]:
                        print("\n" + "="*60)
                        print(f"FINAL ANSWER RECEIVED ({t}):")
                        content = data.get("message", data.get("answer", data.get("content", data.get("text", ""))))
                        print(content)
                        print("="*60 + "\n")
                        with open("iran_report_final.md", "w", encoding="utf-8") as f:
                            f.write(content)
                        if t == "final_answer":
                            break
                    
                    elif t == "agent_done":
                        print("Agent finished task.")
                        break
                    else:
                        print(f"[{t}] ...")
                except asyncio.TimeoutError:
                    print("Still waiting for agent activity (timeout 60s)...")
    except Exception as e:
        print(f"Connection closed or error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
