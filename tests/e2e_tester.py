import asyncio
import websockets
import json
import uuid
import time
from typing import Dict, Any, List

async def run_archimedes_task(task_text: str, session_id: str = None, timeout: int = 400):
    if not session_id:
        session_id = f"test_{uuid.uuid4().hex[:8]}"
    
    uri = f"ws://127.0.0.1:8001/ws/{session_id}"
    print(f"[{session_id}] Connecting to {uri}...")
    report: Dict[str, Any] = {
        "task": task_text,
        "status": "FAILED",
        "iterations": 0,
        "model": "Groq/Gemini",
        "problems": [],
        "result": "",
        "events": []
    }
    
    start_time = time.time()
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{session_id}] Connected!")
            # Send task
            await websocket.send(json.dumps({"task": task_text}))
            
            while time.time() - start_time < timeout:
                try:
                    # Wait for message with timeout to avoid hanging
                    message = await asyncio.wait_for(websocket.recv(), timeout=120)
                    event = json.loads(message)
                    report["events"].append(event)
                    
                    if event["type"] == "thought":
                        print(f"[{session_id}] Thought: {event['content'][:100]}...")
                    
                    if event["type"] == "tool_call":
                        report["iterations"] += 1
                        print(f"[{session_id}] Tool Call: {event['tool']}({event['params']})")
                    
                    if event["type"] == "tool_result":
                        if not event.get("success", True):
                            report["problems"].append(f"Tool {event['tool']} failed: {event.get('error')}")
                    
                    if event["type"] == "message_info":
                        report["result"] = event["text"]
                    
                    if event["type"] == "tool_call" and event["tool"] == "message" and event["params"].get("type") == "result":
                        report["status"] = "SUCCESS"
                        report["result"] = event["params"].get("content", "")
                        break
                        
                    if event["type"] == "agent_error":
                        report["problems"].append(event["message"])
                        break
                        
                    if event["type"] == "session_end":
                        if event["reason"] == "max_iterations":
                            report["problems"].append("Reached max iterations")
                        break
                        
                except asyncio.TimeoutError:
                    report["problems"].append("Timeout waiting for message")
                    break
    except Exception as e:
        report["problems"].append(f"Connection error: {e}")
        
    return report

async def main():
    tasks = [
        "Напиши краткое эссе о философе Архимеде на 200 слов и сохрани в файл archimedes_essay.txt",
        "Найди топ-5 самых популярных Python библиотек в 2026 году и сделай сравнительную таблицу в Markdown",
        "Напиши Python скрипт который парсит погоду с wttr.in для города Алматы и выводит температуру. Запусти его через shell и покажи результат",
        "Создай простую статическую веб-страницу (index.html) с красивым дизайном — landing page для продукта Archimedes AI. Используй CSS внутри HTML. Запусти её и убедись что она доступна (просто сохрани файл)",
        "Зайди на github.com/trending, найди топ-3 репозитория за сегодня, изучи каждый и создай текстовый отчёт (отчёт.txt) с описанием каждого проекта"
    ]
    
    results = []
    for i, t in enumerate(tasks):
        print(f"\n--- Running Task {i+1} ---")
        res = await run_archimedes_task(t)
        results.append(res)
        print(f"[{res.get('status')}] Task {i+1} finished. Cooling down for 10s...")
        await asyncio.sleep(10)
    
    # Print final summary
    print("\n\n" + "="*50)
    print("ARCHIMEDES E2E TEST REPORT")
    print("="*50)
    for i, res in enumerate(results):
        print(f"\nTask {i+1}: {tasks[i][:50]}...")
        print(f"Status: {res.get('status', 'FAILED')}")
        print(f"Iterations: {res.get('iterations', 0)}")
        print(f"Problems: {'; '.join(res.get('problems', [])) if res.get('problems') else 'None'}")
        print(f"Result (short): {str(res.get('result', ''))[:200]}...")
    
if __name__ == "__main__":
    import sys
    import io
    if sys.platform == "win32":
        # Use UTF-8 for output
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
    asyncio.run(main())
