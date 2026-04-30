"""Tests for auto-compact engine."""
import pytest
from backend.memory.auto_compact import AutoCompact, CompactConfig, CompactLevel, MessagePriority, TokenBudget


def _make_messages(n: int, content_size: int = 100) -> list:
    msgs = [{"role": "system", "content": "You are an assistant."}]
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": "x" * content_size})
    return msgs


class TestAutoCompact:
    def test_no_compact_small_context(self):
        import asyncio
        ac = AutoCompact(CompactConfig(max_context_tokens=10000))
        msgs = _make_messages(5, 100)
        result_msgs, result = asyncio.run(ac.maybe_compact(msgs))
        assert result.level == CompactLevel.NONE
        assert len(result_msgs) == len(msgs)

    def test_micro_compact_trims_tool_output(self):
        ac = AutoCompact(CompactConfig(max_context_tokens=500))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "tool", "content": "x" * 1000, "tool_call_id": "t1"},
        ]
        compacted = ac.micro_compact(msgs)
        assert len(compacted[1]["content"]) < 1000

    def test_aggressive_keeps_recent(self):
        ac = AutoCompact(CompactConfig(preserve_recent=5))
        msgs = _make_messages(50, 100)
        compacted = ac.aggressive_compact(msgs, "summary of old conversation")
        assert len(compacted) <= 7  # system + summary + last 5

    def test_estimate_tokens(self):
        ac = AutoCompact()
        msgs = [{"role": "user", "content": "x" * 400}]
        tokens = ac.estimate_tokens(msgs)
        assert tokens == 100  # 400 chars / 4

    def test_extractive_summary_finds_errors(self):
        ac = AutoCompact()
        msgs = [
            {"role": "assistant", "content": "Error: ModuleNotFoundError happened"},
            {"role": "user", "content": "regular message"},
        ]
        summary = ac._extractive_summary(msgs)
        assert "Error" in summary


class TestMessagePriority:
    def test_system_is_critical(self):
        msg = {"role": "system", "content": "You are Archimedes"}
        assert MessagePriority.for_message(msg, 0, 10) == MessagePriority.CRITICAL

    def test_recent_user_is_critical(self):
        msg = {"role": "user", "content": "Fix this bug"}
        assert MessagePriority.for_message(msg, 9, 10) == MessagePriority.CRITICAL

    def test_error_is_high(self):
        msg = {"role": "tool", "content": "Error: file not found"}
        assert MessagePriority.for_message(msg, 3, 10) == MessagePriority.HIGH

    def test_old_tool_is_ephemeral(self):
        msg = {"role": "tool", "content": "output data"}
        assert MessagePriority.for_message(msg, 1, 10) == MessagePriority.EPHEMERAL


class TestPriorityPrune:
    def test_prune_removes_low_priority(self):
        ac = AutoCompact(CompactConfig(max_context_tokens=500))
        messages = [{"role": "system", "content": "system"}]
        for i in range(10):
            messages.append({"role": "user" if i % 2 == 0 else "assistant", "content": "old msg"})
        messages.extend([
            {"role": "tool", "content": "x" * 200},
            {"role": "tool", "content": "y" * 200},
            {"role": "user", "content": "recent question"},
        ])
        result = ac.priority_prune(messages, 50)
        assert len(result) < len(messages)
        assert result[0]["role"] == "system"
        assert result[-1]["role"] == "user"


class TestPostCompactCleanup:
    def test_remove_empty_messages(self):
        ac = AutoCompact()
        messages = [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "hello"},
        ]
        result = ac.post_compact_cleanup(messages)
        assert len(result) == 2

    def test_remove_orphaned_tool_response(self):
        ac = AutoCompact()
        messages = [
            {"role": "system", "content": "system"},
            {"role": "tool", "content": "result", "tool_call_id": "orphan_123"},
            {"role": "user", "content": "hello"},
        ]
        result = ac.post_compact_cleanup(messages)
        assert len(result) == 2


class TestTokenBudget:
    def test_remaining_calculation(self):
        budget = TokenBudget(total=28000)
        assert budget.remaining(20000) == 7000
