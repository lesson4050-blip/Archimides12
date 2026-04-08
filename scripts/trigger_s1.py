import asyncio
import websockets
import json
import datetime
import os

async def run_task():
    session_id = "task_s1_crm"
    url = f"ws://localhost:8001/ws/{session_id}"
    log_file = "d:/Cosmo/workspace/benchmark_reports/task_s1_crm_log.txt"
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    task_text = """ЗАДАЧА УРОВНЯ S: Аналитик Open Source CRM.
1. Найди на GitHub 3 самые популярные Open Source CRM-системы.
2. Для каждой создай в воркспейсе папку с её названием.
3. Внутри каждой папки создай файл analysis.md со списком сильных и слабых сторон (на РУССКОМ ЯЗЫКЕ).
4. Составь сводную таблицу сравнения в /home/ubuntu/workspace/comparison.md.
5. Создай КРАСИВУЮ HTML-презентацию /home/ubuntu/workspace/presentation.html (один файл, CSS/JS внутри).
   - Презентация должна визуализировать твой выбор лучшей системы.
   - Используй библиотеку Chart.js для графиков сравнения (через CDN).
   - Дизайн должен быть премиальным (используй градиенты, современные шрифты и анимации).
6. В конце проверь, что все папки и файлы на месте.

ПРАВИЛО: Будь предельно внимателен к деталям. Не ленись. Используй браузер для глубокого изучения каждого проекта.
"""

    async with websockets.connect(url) as websocket:
        print(f"[{datetime.datetime.now()}] Connected to {url}")
        
        # Start task
        await websocket.send(json.dumps({"task": task_text}))
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] Connection established.\n")
            f.write(f"[{datetime.datetime.now()}] Sending S-Level Task 1...\n")
            
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    log_entry = f"[{timestamp}] Received: {json.dumps(data, indent=2, ensure_ascii=False)}\n"
                    f.write(log_entry)
                    f.flush()
                    
                    if data.get("type") == "result":
                        print("Task finished.")
                        break
                    elif data.get("type") == "error":
                        print(f"Error: {data.get('message')}")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed.")
                    break

if __name__ == "__main__":
    asyncio.run(run_task())
