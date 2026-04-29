"""Tests for auto-compact engine."""
import pytest
from backend.memory.auto_compact import AutoCompact, CompactConfig, CompactLevel


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
