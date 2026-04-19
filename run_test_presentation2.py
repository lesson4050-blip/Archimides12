import asyncio, os
from backend.cosmo.engine import start_engine
from backend.tools.cosmo_tool import CosmoPresentationTool

async def test():
    print('Starting COSMO engine...')
    started = await start_engine()
    print(f'Engine started: {started}')

    print('Generating test presentation...')
    tool = CosmoPresentationTool()
    result = await tool.execute(
        prompt=(
            'Archimedes AI Agent: как один разработчик создал агента '
            'который превзошёл Manus AI.'
        ),
        slide_count=10,
        theme='dark',
        language='ru',
        filename='archimedes_test_presentation'
    )
    print('Result:', result.get('success'))
    print('File:', result.get('file_path'))
    print('Size:', result.get('file_size_kb'), 'KB')
    print('Output:', result.get('output'))
    return result

if __name__ == "__main__":
    asyncio.run(test())
