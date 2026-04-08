import asyncio
import websockets
import json
import datetime
import os

async def run_task():
    session_id = "task12"
    url = f"ws://localhost:8001/ws/{session_id}"
    log_file = "d:/Cosmo/workspace/benchmark_reports/task12_log.txt"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as f:
        async with websockets.connect(url) as websocket:
            f.write(f"[{datetime.datetime.now()}] Connected to {url}\n")
            f.flush()

            task_msg = {
                "task": "Собери актуальные данные по топ-20 криптовалютам (Bitcoin, Ethereum, Solana и др.). Найди их текущие цены и рыночную капитализацию. Составь отчет в виде таблицы в файле /home/ubuntu/workspace/crypto_prices_top20.md. Все заголовки и текст должны быть на русском языке. Обязательно используй браузер (Playwright) для получения самых свежих данных с CoinMarketCap или подобных сайтов. Выполни проверку результата перед финальным ответом."
            }
            await websocket.send(json.dumps(task_msg))
            f.write(f"[{datetime.datetime.now()}] Sending task: {task_msg['task']}\n")
            f.flush()

            try:
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    f.write(f"[{datetime.datetime.now()}] Received: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                    f.flush()
                    
                    # Stop if task is explicitly completed or error
                    if data.get("type") == "tool_call" and data.get("tool") == "message" and data.get("params", {}).get("action") == "result":
                        f.write(f"[{datetime.datetime.now()}] Task completed.\n")
                        f.flush()
                        break
                    if data.get("type") == "agent_error":
                        f.write(f"[{datetime.datetime.now()}] Agent error: {data.get('message')}\n")
                        f.flush()
                        break
            except websockets.exceptions.ConnectionClosed:
                f.write(f"[{datetime.datetime.now()}] Connection closed.\n")
                f.flush()

if __name__ == "__main__":
    asyncio.run(run_task())
