import requests
import json

url = "http://localhost:8001/task"
payload = {
    "task_id": "task12",
    "task_prompt": "Собери актуальные данные по топ-20 криптовалютам (Bitcoin, Ethereum, Solana и др.). Найди их текущие цены и рыночную капитализацию. Составь отчет в виде таблицы в файле /home/ubuntu/workspace/crypto_prices_top20.md. Все заголовки и текст должны быть на русском языке. Обязательно используй браузер (Playwright) для получения самых свежих данных с CoinMarketCap или подобных сайтов. Выполни проверку результата перед финальным ответом."
}
headers = {'Content-Type': 'application/json'}

response = requests.post(url, data=json.dumps(payload), headers=headers)
print(response.status_code)
print(response.text)
