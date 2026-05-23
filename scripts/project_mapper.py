import os
import ast
import re
from pathlib import Path

class ProjectMapper:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.ignore_dirs = {
            '.git', '.agents', '.github', '.pytest_cache', 'node_modules', 
            'venv', '__pycache__', 'chroma', 'chroma_db', 'logs', 'dist', 'build'
        }
        self.ignore_files = {'.gitignore', '.env', 'requirements.txt', 'pyproject.toml'}
        self.map_file = self.root_dir / "PROJECT_MAP.md"

    def is_ignored(self, path):
        for part in path.parts:
            if part in self.ignore_dirs:
                return True
        return path.name in self.ignore_files

    def analyze_python(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            summary = {"classes": [], "functions": []}
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    summary["classes"].append({"name": node.name, "methods": methods})
                elif isinstance(node, ast.FunctionDef):
                    summary["functions"].append(node.name)
            return summary
        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_ts(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex for TS/TSX
            interfaces = re.findall(r'interface\s+(\w+)', content)
            types = re.findall(r'type\s+(\w+)', content)
            functions = re.findall(r'(?:function|const)\s+(\w+)\s*[:=]\s*(?:\([^)]*\)|async)', content)
            components = re.findall(r'const\s+(\w+)\s*:\s*React\.(?:FC|FunctionComponent)', content)
            
            return {
                "interfaces": interfaces,
                "types": types,
                "functions": list(set(functions)),
                "components": components
            }
        except Exception as e:
            return f"Error: {str(e)}"

    def get_phase(self, rel_path):
        path_str = str(rel_path).replace('\\', '/')
        
        # Phase 5: Presentation Engine & Visual Analysis
        if (path_str.startswith('backend/api/marp') or
            path_str.startswith('backend/agent/tools/canvas') or
            path_str.startswith('backend/agent/vision_feedback') or
            path_str.startswith('backend/security/vuln_scanner') or
            'appshots' in path_str.lower() or
            'appshot' in path_str.lower()):
            return "Phase 5: Visuals & Scanning"
            
        # Phase 4: Restricted Execution & Sandbox Hardening
        if (path_str.startswith('backend/sandbox') or
            path_str.startswith('backend/security') or
            path_str.startswith('backend/tools/bash_security') or
            path_str.startswith('backend/auth') or
            'security' in path_str.lower()):
            return "Phase 4: Sandbox & Hardening"
            
        # Phase 3: Cognitive Swarm & MCTS Reasoning
        if (path_str.startswith('backend/agent/core') or
            path_str.startswith('backend/agent/orchestration') or
            path_str.startswith('backend/agent/intelligence') or
            path_str.startswith('backend/agent/skills') or
            path_str.startswith('backend/agent/planner') or
            path_str.startswith('backend/agent/session_store') or
            path_str.startswith('backend/agent/shared_blackboard') or
            path_str.startswith('backend/agent/skill') or
            path_str.startswith('backend/memory') or
            'mcts' in path_str.lower() or
            'swarm' in path_str.lower()):
            return "Phase 3: Cognitive & Swarm"
            
        # Phase 2: Decoupled UI & Zustand State
        if (path_str.startswith('frontend') or
            'zustand' in path_str.lower() or
            path_str.endswith('.tsx')):
            return "Phase 2: Zustand & UI"
            
        # Phase 1: Core Engine & Unified Routing (and general fallbacks)
        if (path_str.startswith('backend/main') or
            path_str.startswith('backend/config') or
            path_str.startswith('backend/run') or
            path_str.startswith('backend/telemetry') or
            path_str.startswith('backend/metrics') or
            path_str.startswith('backend/websocket') or
            path_str.startswith('backend/middleware') or
            path_str.startswith('backend/db') or
            path_str.startswith('backend/models') or
            path_str.startswith('backend/api')):
            return "Phase 1: Core & Routing"
            
        # Context-based folder fallbacks
        if 'agent' in path_str or 'memory' in path_str:
            return "Phase 3: Cognitive & Swarm"
        if 'sandbox' in path_str or 'auth' in path_str:
            return "Phase 4: Sandbox & Hardening"
        if 'frontend' in path_str:
            return "Phase 2: Zustand & UI"
        if 'marp' in path_str or 'canvas' in path_str or 'vuln' in path_str:
            return "Phase 5: Visuals & Scanning"
            
        return "Phase 1: Core & Routing"

    def generate(self):
        output = ["# 🗺️ Project Architecture Map: Cosmo / Archimedes\n"]
        output.append("> This file is automatically generated to provide context for AI agents.\n")
        output.append("> Each component and file is tagged with its corresponding development phase.\n")
        
        sections = {}

        for file_path in self.root_dir.rglob('*'):
            # Skip scratch directory entirely during mapping
            if "scratch" in file_path.parts:
                continue
                
            if file_path.is_file() and not self.is_ignored(file_path):
                rel_path = file_path.relative_to(self.root_dir)
                ext = file_path.suffix
                
                # Group by top-level directory
                parts = rel_path.parts
                top_dir = parts[0] if len(parts) > 1 else "Root"
                
                if top_dir not in sections:
                    sections[top_dir] = []
                
                info = {"path": str(rel_path), "ext": ext}
                info["phase"] = self.get_phase(rel_path)
                
                if ext == '.py':
                    info["analysis"] = self.analyze_python(file_path)
                elif ext in ['.ts', '.tsx']:
                    info["analysis"] = self.analyze_ts(file_path)
                
                sections[top_dir].append(info)

        for section, files in sorted(sections.items()):
            output.append(f"## 📁 {section}")
            for f in files:
                output.append(f"### 📄 `{f['path']}` — `[{f['phase']}]`")
                analysis = f.get("analysis")
                if isinstance(analysis, dict):
                    if "classes" in analysis and analysis["classes"]:
                        output.append("**Classes:**")
                        for c in analysis["classes"]:
                            output.append(f"- `{c['name']}` (Methods: {', '.join(c['methods'][:5])}{'...' if len(c['methods']) > 5 else ''})")
                    if "functions" in analysis and analysis["functions"]:
                        output.append(f"**Functions:** `{', '.join(analysis['functions'][:10])}`")
                    if "components" in analysis and analysis["components"]:
                        output.append(f"**React Components:** `{', '.join(analysis['components'])}`")
                output.append("")

        with open(self.map_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print(f"[SUCCESS] Map generated at {self.map_file}")

if __name__ == "__main__":
    mapper = ProjectMapper(".")
    mapper.generate()

