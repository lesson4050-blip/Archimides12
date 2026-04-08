import asyncio
import websockets
import json
import datetime
import os

async def run_task():
    session_id = "task12_v2"
    url = f"ws://localhost:8001/ws/{session_id}"
    log_file = "d:/Cosmo/workspace/benchmark_reports/task12_v2_log.txt"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] Attempting connection to {url}\n")
        f.flush()
        try:
            async with websockets.connect(url, open_timeout=60) as websocket:
                f.write(f"[{datetime.datetime.now()}] Connected.\n")
                f.flush()

                task_msg = {
                    "task": "Твоя предыдущая попытка (task12) провалилась: ты написал 'Данные не извлечены' для большинства монет, хотя данные были в выводе браузера. БУДЬ ВНИМАТЕЛЬНЕЕ. Собери полные актуальные данные по ТОП-20 криптовалютам. Для КАЖДОЙ из 20 монет найди: Название, Тикер, Текущая цена (USD), Рыночная капитализация. Составь отчет в виде таблицы в файле /home/ubuntu/workspace/crypto_prices_top20.md. Все заголовки и текст должны быть на русском языке. Обязательно используй браузер (Playwright) или поиск. НЕЗАВЕРШЕННЫЕ ДАННЫЕ НЕПРИЕМЛЕМЫ. Выполни проверку результата перед финальным ответом. Сделай все одним файлом."
                }
                await websocket.send(json.dumps(task_msg))
                f.write(f"[{datetime.datetime.now()}] Sending task: {task_msg['task']}\n")
                f.flush()

                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    f.write(f"[{datetime.datetime.now()}] Received: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                    f.flush()
                    
                    if data.get("type") == "tool_call" and data.get("tool") == "message" and data.get("params", {}).get("action") == "result":
                        f.write(f"[{datetime.datetime.now()}] Task completed.\n")
                        f.flush()
                        break
                    if data.get("type") == "agent_error":
                        f.write(f"[{datetime.datetime.now()}] Agent error: {data.get('message')}\n")
                        f.flush()
                        break
        except Exception as e:
            f.write(f"[{datetime.datetime.now()}] Error: {str(e)}\n")
            f.flush()

if __name__ == "__main__":
    asyncio.run(run_task())
