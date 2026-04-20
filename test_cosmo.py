import asyncio
import sys
import os
import json
import psutil

# Enforce the new model for Ollama
os.environ["OLLAMA_MODEL"] = "qwen2.5:14b"

sys.path.insert(0, '.')
from backend.cosmo.engine import start_engine, stop_engine, get_engine_url
from backend.tools.cosmo_tool import CosmoPresentationTool

def kill_old_engine():
    # Kill any python processes running 'uvicorn api.main:app --port 5051'
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmd = p.info.get('cmdline')
        if cmd and 'uvicorn' in cmd and 'api.main:app' in cmd:
            print(f"Killing old uvicorn engine process: {p.pid}")
            p.kill()

async def test():
    print('Terminating any hung background engines...')
    kill_old_engine()
    
    print('Starting COSMO engine with model:', os.environ["OLLAMA_MODEL"])
    ok = await start_engine()
    print(f'Engine started successfully: {ok}')
    
    if not ok:
        print("Failed to start engine")
        return
        
    print(f'Engine URL: {get_engine_url()}')
    
    tool = CosmoPresentationTool()
    print('Sending prompt to engine. Generating presentation (4 slides) using Qwen2.5:14b...')
    
    try:
        # Smaller prompt and 4 slides to be fast
        result = await tool.execute(
            prompt='Сравнение агентов: Manus, OpenHands, Devin',
            slide_count=4,
            language='Russian',
            filename='qwen_demo'
        )
        
        print('\n--- RESULT ---')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == '__main__':
    asyncio.run(test())
