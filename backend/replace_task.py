import os
import re

def main():
    backend_dir = r"d:\Cosmo\backend"
    exclude_files = ["search_tool.py", "crud.py", "registry.py", "routes.py", "task.py"]
    
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            if file in exclude_files:
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if "safe_create_task" in content:
                # Add import right after the first line or other imports
                if "from backend.utils.task import safe_create_task" not in content:
                    lines = content.splitlines()
                    import_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("import ") or line.startswith("from "):
                            import_idx = i
                            break
                    lines.insert(import_idx, "from backend.utils.task import safe_create_task")
                    content = "\n".join(lines)
                
                # Replace safe_create_task
                content = content.replace("safe_create_task", "safe_create_task")
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Updated {filepath}")

if __name__ == "__main__":
    main()
