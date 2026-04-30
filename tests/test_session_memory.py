"""Tests for SessionMemory."""
import pytest
import os
from unittest.mock import patch


@pytest.mark.asyncio
async def test_extract_key_info_finds_errors(tmp_path):
    with patch("backend.memory.session_memory.SESSION_MEMORY_DIR", str(tmp_path)):
        from backend.memory.session_memory import SessionMemory
        sm = SessionMemory("test-session")
        msgs = [
            {"role": "assistant", "content": "Error: FileNotFoundError occurred"},
            {"role": "user", "content": "Fix the bug"},
        ]
        result = sm._extract_key_info(msgs)
        assert "Error" in result


@pytest.mark.asyncio
async def test_extract_key_info_finds_files(tmp_path):
    with patch("backend.memory.session_memory.SESSION_MEMORY_DIR", str(tmp_path)):
        from backend.memory.session_memory import SessionMemory
        sm = SessionMemory("test-session")
        msgs = [{"role": "assistant", "content": "Modified backend/agent/core.py successfully"}]
        result = sm._extract_key_info(msgs)
        assert "backend/agent/core.py" in result


def test_list_recent_sessions_empty(tmp_path):
    with patch("backend.memory.session_memory.SESSION_MEMORY_DIR", str(tmp_path)):
        from backend.memory.session_memory import SessionMemory
        sessions = SessionMemory.list_recent_sessions()
        assert isinstance(sessions, list)


class TestCrossSessionSearch:
    def test_search_returns_list(self, tmp_path):
        with patch("backend.memory.session_memory.SESSION_MEMORY_DIR", str(tmp_path)):
            from backend.memory.session_memory import SessionMemory
            results = SessionMemory.search_past_sessions("test query")
            assert isinstance(results, list)

    def test_search_finds_relevant_session(self, tmp_path):
        with patch("backend.memory.session_memory.SESSION_MEMORY_DIR", str(tmp_path)):
            mem_file = tmp_path / "session_abc.md"
            mem_file.write_text("## Current Task\nFix the authentication bug")
            from backend.memory.session_memory import SessionMemory
            results = SessionMemory.search_past_sessions("authentication bug")
            assert len(results) > 0
            assert results[0]["session_id"] == "session_abc"
