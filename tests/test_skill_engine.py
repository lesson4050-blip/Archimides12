import pytest
import os
import json
import shutil
from backend.agent.skill_engine import compress_skill, find_matching_skill, _templatize_params, _extract_keywords, SKILLS_DIR

def setup_module(module):
    """Setup test skills directory."""
    if os.path.exists(SKILLS_DIR):
        shutil.rmtree(SKILLS_DIR)
    os.makedirs(SKILLS_DIR, exist_ok=True)

def teardown_module(module):
    """Clean up after tests."""
    if os.path.exists(SKILLS_DIR):
        shutil.rmtree(SKILLS_DIR)

def test_templatize_params():
    params = {
        "path": "d:/Cosmo/backend/agent/test.py",
        "url": "https://api.github.com/repo",
        "action": "write",
        "code": "print('hello')"
    }
    templated = _templatize_params(params)
    assert templated["path"] == "{{path}}"
    assert templated["url"] == "{{url}}"
    assert templated["action"] == "write"
    assert templated["code"] == "print('hello')"

def test_compress_skill_trivial():
    # Should return None for < 3 tool calls
    result = compress_skill("test task", [{"name": "tool1", "params": {}}], "done")
    assert result is None

def test_compress_and_find_skill():
    task = "setup new react project with vite"
    tool_calls = [
        {"name": "run_command", "params": {"cmd": "npx create-vite ."}, "success": True},
        {"name": "run_command", "params": {"cmd": "npm install"}, "success": True},
        {"name": "write_file", "params": {"path": "src/App.jsx", "content": "hello"}, "success": True}
    ]
    
    # 1. Compress
    skill_file = compress_skill(task, tool_calls, "success", session_id="test1234")
    assert skill_file is not None
    
    full_path = os.path.join(SKILLS_DIR, skill_file)
    assert os.path.exists(full_path)
    
    with open(full_path, "r") as f:
        skill_data = json.load(f)
        
    assert skill_data["trigger"]["intent"] == task
    assert skill_data["total_steps"] == 3
    assert skill_data["steps"][2]["params_template"]["path"] == "{{path}}"
    
    # 2. Find matching
    match = find_matching_skill("setup a new react project with vite")
    assert match is not None
    assert match["session_id"] == "test1234"
    
    # 3. Find non-matching
    no_match = find_matching_skill("configure nginx server")
    assert no_match is None
