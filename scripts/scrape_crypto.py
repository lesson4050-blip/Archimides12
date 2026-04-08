import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

def scrape_top_20():
    url = "https://coinmarketcap.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # CoinMarketCap uses a table with class 'cmc-table'
    table = soup.find('table', class_='cmc-table')
    if not table:
        print("Table not found")
        return

    rows = table.find_all('tr')[1:21] # Get first 20 coins (skip header)
    
    data = []
    for i, row in enumerate(rows):
        cols = row.find_all('td')
        if len(cols) < 5: continue
        
        # Structure varies, but usually: #, Name, Price, 24h, Market Cap
        # The name and symbol are often inside a div/p
        name_p = cols[2].find('p', class_='coin-item-name')
        symbol_p = cols[2].find('p', class_='coin-item-symbol')
        
        if not name_p:
            # Fallback for different CMC versions
            name_p = cols[2].find('span', class_='crypto-symbol')
            
        name = name_p.text if name_p else "Unknown"
        symbol = symbol_p.text if symbol_p else ""
        
        price = cols[3].text
        market_cap = cols[7].text if len(cols) > 7 else "N/A"
        
        data.append({
            "№": i + 1,
            "Название": name,
            "Символ": symbol,
            "Цена (USD)": price,
            "Рыночная капитализация (USD)": market_cap
        })

    df = pd.DataFrame(data)
    md_content = "# Топ-20 криптовалют по рыночной капитализации\n\n"
    md_content += df.to_markdown(index=False)
    
    output_path = "/home/ubuntu/workspace/crypto_prices_top20.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"Successfully saved {len(data)} coins to {output_path}")

if __name__ == "__main__":
    scrape_top_20()
