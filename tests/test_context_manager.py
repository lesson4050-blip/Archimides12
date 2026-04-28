"""Tests for context manager self-healing."""
import pytest


def _make_context_manager():
    from backend.memory.context_manager import ContextManager
    return ContextManager(max_tokens=4096)


def test_heal_context_removes_empty_messages():
    """Empty content messages must be removed."""
    cm = _make_context_manager()
    cm.history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": ""},  # empty — should be removed
        {"role": "user", "content": "World"},
    ]
    fixed = cm.heal_context()
    assert fixed >= 1
    assert all(m["content"] for m in cm.history)


def test_heal_context_deduplicates_system_messages():
    """Multiple consecutive system messages must be deduplicated."""
    cm = _make_context_manager()
    cm.history = [
        {"role": "system", "content": "First system"},
        {"role": "system", "content": "Second system"},  # duplicate
        {"role": "user", "content": "Hello"},
    ]
    fixed = cm.heal_context()
    assert fixed >= 1
    system_msgs = [m for m in cm.history if m["role"] == "system"]
    assert len(system_msgs) == 1
    # Should keep the LAST system message
    assert system_msgs[0]["content"] == "Second system"


def test_heal_context_removes_orphaned_tool_results():
    """Tool results without preceding tool_calls must be removed."""
    cm = _make_context_manager()
    cm.history = [
        {"role": "user", "content": "Run something"},
        {"role": "tool", "content": "tool result"},  # orphaned — no preceding tool_call
    ]
    fixed = cm.heal_context()
    assert fixed >= 1
    tool_msgs = [m for m in cm.history if m["role"] == "tool"]
    assert len(tool_msgs) == 0


def test_heal_context_preserves_valid_tool_sequence():
    """Valid tool call + result sequence must be preserved."""
    cm = _make_context_manager()
    cm.history = [
        {"role": "user", "content": "Run something"},
        {"role": "assistant", "content": "", "tool_calls": [{"name": "shell"}]},
        {"role": "tool", "content": "command output"},
    ]
    original_count = len(cm.history)
    cm.heal_context()
    # Valid sequence — nothing should be removed
    assert len(cm.history) == original_count
