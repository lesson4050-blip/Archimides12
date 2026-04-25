import pytest
import os
import json
import shutil
from backend.agent.skills.skill_engine import SkillEngine


@pytest.fixture
def engine(tmp_path):
    """Create a SkillEngine with a temporary skills directory."""
    e = SkillEngine()
    e.skills_dir = str(tmp_path / "skills")
    os.makedirs(e.skills_dir, exist_ok=True)
    return e


def test_find_relevant_skill_empty(engine):
    """Should return None when no skills exist."""
    result = engine.find_relevant_skill("setup a new react project")
    assert result is None


def test_extract_and_save_skill_trivial(engine):
    """Should handle trivial history gracefully without crashing."""
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    # Should not raise, even if it produces nothing meaningful
    result = engine.extract_and_save_skill("hello", history, success=True)
    # Result can be None or a valid skill — just verify no crash
    assert result is None or isinstance(result, dict)


def test_get_skill_prompt_injection(engine):
    """Should produce a valid prompt from a skill dict."""
    skill = {
        "task": "deploy app",
        "trigger": {
            "intent": "deploy app",
            "variables": {}
        },
        "steps": [
            {"tool": "shell", "params_template": {"cmd": "npm run build"}, "success": True},
            {"tool": "shell", "params_template": {"cmd": "npm start"}, "success": True},
        ]
    }
    prompt = engine.get_skill_prompt_injection(skill)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_compress_skill_legacy_bridge():
    """Verify the legacy bridge still works."""
    from backend.agent.skill_engine import compress_skill
    steps = [
        {"tool": "shell", "params": {"cmd": "echo hello"}},
        {"tool": "file", "params": {"path": "/tmp/test.py", "content": "print(1)"}},
    ]
    result = compress_skill(steps)
    assert isinstance(result, list)
