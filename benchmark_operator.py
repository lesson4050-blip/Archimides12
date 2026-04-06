import asyncio
import json
import websockets
import sys
import os
from datetime import datetime

async def run_task(session_id, task_text, output_file):
    uri = f"ws://localhost:8001/ws/{session_id}"
    log_file = open(output_file, "w", encoding="utf-8")
    
    def log(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        log_file.write(line)
        log_file.flush()
        print(line, end="")

    try:
        async with websockets.connect(uri) as websocket:
            log(f"Connected to {uri}")
            
            # Wait for session_ready
            async for message in websocket:
                data = json.loads(message)
                log(f"Received: {json.dumps(data, indent=2)}")
                if data.get("type") == "session_ready":
                    break
            
            # Send task
            log(f"Sending task: {task_text}")
            await websocket.send(json.dumps({"task": task_text}))
            
            # Listen for results
            iteration_count = 0
            async for message in websocket:
                data = json.loads(message)
                log(f"Received: {json.dumps(data, indent=2)}")
                
                # Count iterations (thoughts usually indicate a step)
                if data.get("type") == "agent_thought":
                    iteration_count += 1
                
                if data.get("type") == "result":
                    log("SUCCESS: Task completed via result message.")
                    break
                if data.get("type") == "message_info" and not data.get("text", "").startswith("<thought>"):
                    # Log message info but don't exit, unless it looks like a final result.
                    text_content = data.get("text", "")
                    if '{"tool_call":' in text_content:
                        log("WARNING: Found unparsed JSON tool call in message_info. The agent failed to parse it.")
                    elif "Task completed" in text_content or "SUCCESS" in text_content:
                        log("SUCCESS: Task completed via message_info.")
                        break
                    break
                if data.get("type") == "agent_error":
                    log("ERROR: Agent reported an error.")
                    break
            
            log(f"Total iterations: {iteration_count}")
            
    except Exception as e:
        log(f"CONNECTION ERROR: {e}")
    finally:
        log_file.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python benchmark_operator.py <session_id> <task_text> <output_file>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    task_text = sys.argv[2]
    output_file = sys.argv[3]
    
    asyncio.run(run_task(session_id, task_text, output_file))
