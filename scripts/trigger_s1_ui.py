import asyncio
import websockets
import json
import datetime
import os

async def run_task():
    session_id = "task_s1_ui_fix"
    url = f"ws://localhost:8001/ws/{session_id}"
    log_file = "d:/Cosmo/workspace/benchmark_reports/task_s1_ui_fix_log.txt"
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Using the existing container from task_s1_crm if possible, 
    # but the backend might create a new one. 
    # I will tell it to read from /home/ubuntu/workspace.
    
    task_text = """ФИНАЛЬНЫЙ ЭТАП ЗАДАЧИ S: Генерация презентации.
В воркспейсе уже лежат данные:
- comparison.md (сводка)
- Папки SuiteCRM, EspoCRM, FrappeCRM с файлами analysis.md.

Твоя задача:
1. Прочитай эти файлы.
2. Создай КРАСИВУЮ HTML-презентацию /home/ubuntu/workspace/presentation.html.
   - CSS: градиенты, темная тема (glassmorphism), современные шрифты (Inter/Outfit через Google Fonts).
   - JS: используй Chart.js для визуализации сравнения (например, Radar chart или Bar chart на основе данных из comparison.md).
   - Анимации при загрузке.
3. Убедись, что файл сохранен и презентация выглядит дорого.
"""

    async with websockets.connect(url) as websocket:
        print(f"[{datetime.datetime.now()}] Connected to {url}")
        await websocket.send(json.dumps({"task": task_text}))
        
        with open(log_file, "a", encoding="utf-8") as f:
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    f.write(f"[{timestamp}] Received: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                    f.flush()
                    
                    if data.get("type") == "result":
                        break
                    elif data.get("type") == "error":
                        break
                except Exception:
                    break

if __name__ == "__main__":
    asyncio.run(run_task())
