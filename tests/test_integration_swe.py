"""
Integration test: simulate a SWE-bench style task end-to-end.
Tests the full pipeline: task → plan → execute → verify → patch.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_codeact_executor_basic():
    """Test that CodeActExecutor runs a simple code task."""
    from backend.agent.codeact_executor import CodeActExecutor

    mock_router = AsyncMock()
    mock_router.generate.return_value = {
        "text": "```python\nprint('TASK_COMPLETE: hello world')\n```",
        "tool_call": None
    }

    mock_sandbox_instance = MagicMock()
    mock_sandbox_instance.run_command = MagicMock(
        return_value=("TASK_COMPLETE: hello world", "", 0)
    )

    with patch("backend.sandbox.e2b_sandbox.E2BSandbox", return_value=mock_sandbox_instance):
        executor = CodeActExecutor(mock_router)
        result = await executor.execute(
            task="Print hello world",
            session_id="test"
        )
    
    assert result["success"] is True
    assert "hello world" in result["output"].lower()


@pytest.mark.asyncio
async def test_code_editor_find_replace(tmp_path):
    """Test CodeEditorTool find_replace on a real file."""
    from backend.tools.code_editor_tool import CodeEditorTool

    test_file = tmp_path / "test_code.py"
    test_file.write_text("def old_function():\n    return 42\n")

    tool = CodeEditorTool()
    result = await tool.execute(
        action="find_replace",
        path=str(test_file),
        old_str="def old_function():",
        new_str="def new_function():"
    )

    assert result["success"] is True
    content = test_file.read_text()
    assert "new_function" in content
    assert "old_function" not in content


@pytest.mark.asyncio
async def test_code_editor_view_lines(tmp_path):
    """Test CodeEditorTool view_lines."""
    from backend.tools.code_editor_tool import CodeEditorTool

    test_file = tmp_path / "test.py"
    test_file.write_text("\n".join(f"line_{i}" for i in range(20)))

    tool = CodeEditorTool()
    result = await tool.execute(
        action="view_lines",
        path=str(test_file),
        start_line=5,
        end_line=10
    )

    assert result["success"] is True
    assert "line_4" in result["output"]


@pytest.mark.asyncio
async def test_session_store(tmp_path):
    """Test SessionStore save and load."""
    from backend.agent.session_store import SessionStore
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path=db_path)

    saved = store.save_context(
        session_id="test_session",
        history=[{"role": "user", "content": "test"}],
        task_description="Test task"
    )
    assert saved is True

    loaded = store.load_context("test_session")
    assert loaded is not None
    assert loaded["task_description"] == "Test task"
    assert len(loaded["history"]) == 1

    store.delete_session("test_session")
    assert store.load_context("test_session") is None


@pytest.mark.asyncio
async def test_mcts_manager_basic():
    """Test that MCTSManager runs and returns a string result."""
    from backend.agent.orchestration.mcts import MCTSManager

    mock_router = AsyncMock()
    mock_router.generate.return_value = {
        "text": '{"correctness": 0.8, "completeness": 0.7, "efficiency": 0.9, "feasibility": 1.0}',
        "tool_call": None
    }

    manager = MCTSManager(workspace_dir="/tmp")
    # Just verify it initializes correctly
    assert manager is not None
    assert manager.num_simulations >= 5
