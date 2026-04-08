import asyncio
import websockets
import json
import datetime
import os

async def run_task():
    session_id = "task12_v3"
    url = f"ws://localhost:8001/ws/{session_id}"
    log_file = "d:/Cosmo/workspace/benchmark_reports/task12_v3_log.txt"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] Attempting connection to {url}\n")
        f.flush()
        try:
            async with websockets.connect(url, open_timeout=60) as websocket:
                f.write(f"[{datetime.datetime.now()}] Connected.\n")
                f.flush()

                task_msg = {
                    "task": "Твои предыдущие попытки (task12, task12_v2) провалились: ты написал 'Данные не извлечены' для большинства монет. ЭТО НЕПРИЕМЛЕМО. Стратегия для успеха: 1. Составь список ТОП-20 монет. 2. Для каждой монеты найди актуальную цену и капитализацию отдельным поиском или внимательным парсингом. 3. Все 20 строк должны быть заполнены точными данными. 4. Сохрани в /home/ubuntu/workspace/crypto_prices_top20.md в виде таблицы на РУССКОМ ЯЗЫКЕ. 5. Обязательно проверь результат сам перед завершением. Если данных нет - ищи снова. Покажи, что ты профи."
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
