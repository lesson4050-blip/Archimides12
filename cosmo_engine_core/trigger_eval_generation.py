import requests
import json
import time

def trigger_generation():
    url = "http://127.0.0.1:5051/api/v1/ppt/presentation/generate/async"
    
    payload = {
        "content": "Будущее дизайна презентаций с использованием искусственного интеллекта. Тренды 2026 года, адаптивная верстка, автоматическая генерация контента и персонализация.",
        "instructions": "Создай профессиональную презентацию на русском языке. Сфокусируйся на инновациях и технологиях. Минимум 8 слайдов.",
        "tone": "professional",
        "verbosity": "standard",
        "web_search": False,
        "n_slides": 8,
        "language": "Russian",
        "template": "general"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Triggering generation for: {payload['content'][:50]}...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        status_id = data.get("id")
        print(f"Generation started! Status ID: {status_id}")
        return status_id
    else:
        print(f"Error starting generation: {response.status_code}")
        print(response.text)
        return None

def monitor_generation(status_id):
    url = f"http://127.0.0.1:5051/api/v1/ppt/presentation/status/{status_id}"
    
    print("Monitoring status...")
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status")
                progress = status_data.get("progress", 0)
                print(f"Status: {status} | Progress: {progress}%")
                
                if status == "completed":
                    print("Generation COMPLETED!")
                    print(f"Resulting JSON: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
                    break
                elif status == "failed":
                    print("Generation FAILED!")
                    print(status_data.get("error"))
                    break
            else:
                print(f"Error checking status: {response.status_code}")
        except Exception as e:
            print(f"Polling error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    pid = trigger_generation()
    if pid:
        monitor_generation(pid)
