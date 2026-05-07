"""Tests for session persistence (SQLite-backed SessionStore v2)."""
import pytest


@pytest.mark.asyncio
async def test_save_and_load_session(tmp_path):
    from backend.agent.session_store import SessionStore
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path=db_path)
    
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
    from backend.agent.session_store import SessionStore
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path=db_path)
    
    store.save_context("del-test", [], "task")
    assert store.load_context("del-test") is not None
    
    store.delete_session("del-test")
    assert store.load_context("del-test") is None


@pytest.mark.asyncio
async def test_load_nonexistent_session(tmp_path):
    from backend.agent.session_store import SessionStore
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path=db_path)
    
    result = store.load_context("nonexistent-session-xyz")
    assert result is None


@pytest.mark.asyncio
async def test_list_active_sessions(tmp_path):
    from backend.agent.session_store import SessionStore
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path=db_path)
    
    store.save_context("session-a", [], "task A")
    store.save_context("session-b", [], "task B")
    
    sessions = store.list_active_sessions()
    assert "session-a" in sessions
    assert "session-b" in sessions
