"""Tests for SkillEngine (backend.agent.skills.skill_engine)."""
import pytest
import os
import json
import shutil
from backend.agent.skill_library import SkillLibrary as SkillEngine


@pytest.fixture
def engine(tmp_path):
    """Create a SkillEngine with a temporary skills directory."""
    e = SkillEngine(
        storage_dir=str(tmp_path / "skills_data")
    )
    return e


def test_find_skill_empty(engine):
    """Should return None when no skills exist."""
    result = engine.find_skill("setup a new react project")
    assert result is None


def test_store_skill_trivial(engine):
    """Should handle trivial trajectory gracefully without crashing."""
    trajectory = [
        {"type": "tool", "tool_call": {"name": "shell", "params": {"command": "ls"}}, "result": "file1.txt"},
    ]
    # Should not raise, even if it produces nothing meaningful
    engine.store_skill("list files", trajectory, quality_score=1.0)
    
    # Verify it was stored
    result = engine.find_skill("list files")
    assert result is not None
    assert result["task"] == "list files"


def test_get_context_prompt(engine):
    """Should produce a valid prompt from a task."""
    trajectory = [
        {"type": "tool", "tool_call": {"name": "shell", "params": {"command": "ls"}}, "result": "file1.txt"},
    ]
    engine.store_skill("list files", trajectory, quality_score=1.0)
    
    prompt = engine.get_context_prompt("list files")
    assert isinstance(prompt, str)
    assert "[SKILL LIBRARY]" in prompt


def test_compress_skill_legacy_bridge():
    """Verify the legacy bridge still works."""
    from backend.agent.skill_engine import compress_skill
    steps = [
        {"tool_call": {"name": "shell", "params": {"cmd": "echo hello"}}, "result": "hello"},
    ]
    result = compress_skill(steps)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["tool"] == "shell"
