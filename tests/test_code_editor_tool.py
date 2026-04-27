"""Tests for surgical code editor."""
import pytest
import os


@pytest.mark.asyncio
async def test_find_replace_simple(tmp_path):
    from backend.tools.code_editor_tool import CodeEditorTool
    
    f = tmp_path / "test.py"
    f.write_text("def old_name():\n    return 42\n")
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="find_replace",
        path=str(f),
        old_str="def old_name():",
        new_str="def new_name():"
    )
    
    assert result["success"] is True
    assert "new_name" in f.read_text()
    assert "old_name" not in f.read_text()


@pytest.mark.asyncio
async def test_find_replace_fails_on_missing_string(tmp_path):
    from backend.tools.code_editor_tool import CodeEditorTool
    
    f = tmp_path / "test.py"
    f.write_text("def foo(): pass\n")
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="find_replace",
        path=str(f),
        old_str="def bar():",  # doesn't exist
        new_str="def baz():"
    )
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_find_replace_fails_on_ambiguous_string(tmp_path):
    from backend.tools.code_editor_tool import CodeEditorTool
    
    f = tmp_path / "test.py"
    f.write_text("x = 1\nx = 1\n")  # duplicate
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="find_replace",
        path=str(f),
        old_str="x = 1",
        new_str="x = 2"
    )
    
    assert result["success"] is False
    assert "ambiguous" in result["error"].lower() or "2" in result["error"]


@pytest.mark.asyncio
async def test_view_lines_returns_correct_range(tmp_path):
    from backend.tools.code_editor_tool import CodeEditorTool
    
    f = tmp_path / "test.py"
    lines = [f"line_{i}\n" for i in range(20)]
    f.write_text("".join(lines))
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="view_lines",
        path=str(f),
        start_line=5,
        end_line=10
    )
    
    assert result["success"] is True
    assert "line_4" in result["output"]  # line 5 (1-indexed) = line_4
    assert "line_0" not in result["output"]


@pytest.mark.asyncio
async def test_insert_after_adds_code(tmp_path):
    from backend.tools.code_editor_tool import CodeEditorTool
    
    f = tmp_path / "test.py"
    f.write_text("def foo():\n    pass\n")
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="insert_after",
        path=str(f),
        old_str="def foo():",
        new_str="    # inserted comment"
    )
    
    assert result["success"] is True
    content = f.read_text()
    assert "inserted comment" in content
    # New code must come AFTER anchor
    anchor_pos = content.index("def foo():")
    insert_pos = content.index("inserted comment")
    assert insert_pos > anchor_pos


@pytest.mark.asyncio
async def test_nonexistent_file_returns_error():
    from backend.tools.code_editor_tool import CodeEditorTool
    
    tool = CodeEditorTool()
    result = await tool.execute(
        action="find_replace",
        path="/nonexistent/path/file.py",
        old_str="foo",
        new_str="bar"
    )
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()
