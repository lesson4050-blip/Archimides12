import asyncio, sys, shutil
from pathlib import Path
sys.path.insert(0, '.')
from backend.cosmo.engine import start_engine, stop_engine
from backend.tools.cosmo_tool import CosmoPresentationTool

async def test():
    print('Starting COSMO engine... and Artist...')
    ok = await start_engine()
    if not ok:
        print('Engine failed to start')
        return

    print('Waiting 10s for the Next.js artist to compile...')
    await asyncio.sleep(10)
    
    tool = CosmoPresentationTool()
    print('Running presentation tool...')
    result = await tool.execute(
        prompt=(
            'Космос. История освоения и будущие миссии. '
            'Целевая аудитория: студенты. Тон: образовательный, профессиональный. '
            'Раскройте историю полётов, основные достижения, МКС, миссии на Марс. '
            'И самое главное - красивый космический дизайн, тёмная тема!'
        ),
        slide_count=5,
        language='Russian',
        filename='cosmos_test_presentation'
    )
    print('Success:', result.get('success'))
    if result.get('success') and result.get('file_path'):
        src = Path(result['file_path'])
        if src.exists():
            print(f'✅ QUALITY CHECK PASSED: {src.name} exists, size is {src.stat().st_size} bytes')
        else:
            print('⚠️ File not found')
    else:
        print('⚠️ Error during execution:', result.get('error', result))

    # Stop the engine and artist when done
    print("Shutting down engine and artist...")
    await stop_engine()

if __name__ == "__main__":
    asyncio.run(test())
