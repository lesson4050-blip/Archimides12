"""Tests for session persistence."""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_save_and_load_session(tmp_path):
    with patch("backend.agent.session_store.SESSION_DIR", tmp_path):
        from backend.agent.session_store import SessionStore
        store = SessionStore()
        
        saved = store.save_context(
            session_id="test-123",
            history=[{"role": "user", "content": "test task"}],
            task_description="Build a REST API",
            current_step=3,
            metadata={"mode": "planning"}
        )
        
        assert saved is True
        
        loaded = store.load_context("test-123")
        assert loaded is not None
        assert loaded["task_description"] == "Build a REST API"
        assert loaded["current_step"] == 3
        assert loaded["metadata"]["mode"] == "planning"
        assert len(loaded["history"]) == 1


@pytest.mark.asyncio
async def test_delete_session(tmp_path):
    with patch("backend.agent.session_store.SESSION_DIR", tmp_path):
        from backend.agent.session_store import SessionStore
        store = SessionStore()
        
        store.save_context("del-test", [], "task")
        assert store.load_context("del-test") is not None
        
        store.delete_session("del-test")
        assert store.load_context("del-test") is None


@pytest.mark.asyncio
async def test_load_nonexistent_session(tmp_path):
    with patch("backend.agent.session_store.SESSION_DIR", tmp_path):
        from backend.agent.session_store import SessionStore
        store = SessionStore()
        
        result = store.load_context("nonexistent-session-xyz")
        assert result is None


@pytest.mark.asyncio
async def test_list_active_sessions(tmp_path):
    with patch("backend.agent.session_store.SESSION_DIR", tmp_path):
        from backend.agent.session_store import SessionStore
        store = SessionStore()
        
        store.save_context("session-a", [], "task A")
        store.save_context("session-b", [], "task B")
        
        sessions = store.list_active_sessions()
        assert "session-a" in sessions
        assert "session-b" in sessions
