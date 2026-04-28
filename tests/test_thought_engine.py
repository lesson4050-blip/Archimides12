"""Tests for ThoughtEngine (test 1.12)."""
import pytest
from backend.agent.thought_engine import ThoughtEngine


def test_get_system_prompt_returns_string():
    """System prompt should be a non-empty string."""
    prompt = ThoughtEngine.get_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100  # it's a long prompt


def test_get_system_prompt_cached():
    """Second call should return cached (same object) prompt."""
    p1 = ThoughtEngine.get_system_prompt()
    p2 = ThoughtEngine.get_system_prompt()
    assert p1 is p2  # same object reference = cached


def test_system_prompt_contains_identity():
    """Prompt must declare Archimedes identity."""
    prompt = ThoughtEngine.get_system_prompt()
    assert "Archimedes" in prompt


def test_system_prompt_contains_action_rules():
    """Prompt must enforce ACTION agent behavior."""
    prompt = ThoughtEngine.get_system_prompt()
    assert "ACTION" in prompt
    assert "tool" in prompt.lower()


def test_system_prompt_contains_tool_list():
    """Prompt must list available tools."""
    prompt = ThoughtEngine.get_system_prompt()
    for tool_name in ["shell", "file", "search", "browser", "code_edit"]:
        assert tool_name in prompt.lower()


def test_system_prompt_contains_swe_bench_protocol():
    """Prompt must include SWE-bench protocol."""
    prompt = ThoughtEngine.get_system_prompt()
    assert "SWE-BENCH" in prompt.upper() or "swe-bench" in prompt.lower()


def test_system_prompt_forbids_editors():
    """Prompt should forbid nano/vim usage."""
    prompt = ThoughtEngine.get_system_prompt()
    assert "nano" in prompt
    assert "vim" in prompt
