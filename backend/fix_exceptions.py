import os
import re

count = 0
for root, dirs, files in os.walk('d:/Cosmo/backend'):
    if 'alembic' in root or 'venv' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple replace to inject logger into bare excepts
            new_content = re.sub(
                r'except\s+Exception\s*:\s*\n(\s+)pass',
                r'except Exception as e:\n\1import logging\n\1logging.getLogger(__name__).warning(f"Blind exception caught: {e}")',
                content
            )
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
                print(f"Fixed {file}")
                
print(f'\nFixed {count} files with blind exceptions')
