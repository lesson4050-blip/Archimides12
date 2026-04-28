"""Tests for CodeEditorTool extended (test 1.17)."""
import os
import pytest
from backend.tools.code_editor_tool import CodeEditorTool


@pytest.fixture
def editor():
    return CodeEditorTool()


@pytest.fixture
def sample_file(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text("def hello():\n    return 'world'\n\ndef foo():\n    return 42\n")
    return str(p)


@pytest.mark.asyncio
async def test_view_lines(editor, sample_file):
    r = await editor.execute(action="view_lines", path=sample_file, start_line=1, end_line=2)
    assert r["success"] is True
    assert "hello" in r["output"]


@pytest.mark.asyncio
async def test_view_function(editor, sample_file):
    r = await editor.execute(action="view_function", path=sample_file, function_name="hello")
    assert r["success"] is True
    assert "hello" in r["output"]


@pytest.mark.asyncio
async def test_view_function_not_found(editor, sample_file):
    r = await editor.execute(action="view_function", path=sample_file, function_name="nonexistent")
    assert r["success"] is False


@pytest.mark.asyncio
async def test_find_replace(editor, sample_file):
    r = await editor.execute(action="find_replace", path=sample_file, old_str="'world'", new_str="'earth'")
    assert r["success"] is True
    with open(sample_file) as f:
        assert "'earth'" in f.read()


@pytest.mark.asyncio
async def test_find_replace_not_found(editor, sample_file):
    r = await editor.execute(action="find_replace", path=sample_file, old_str="NONEXISTENT_STRING_XYZ")
    assert r["success"] is False


@pytest.mark.asyncio
async def test_insert_after(editor, sample_file):
    r = await editor.execute(action="insert_after", path=sample_file, old_str="def hello():", new_str="    # inserted comment")
    assert r["success"] is True


@pytest.mark.asyncio
async def test_insert_before(editor, sample_file):
    r = await editor.execute(action="insert_before", path=sample_file, old_str="def foo():", new_str="# before foo")
    assert r["success"] is True


@pytest.mark.asyncio
async def test_delete_block(editor, sample_file):
    r = await editor.execute(action="delete_block", path=sample_file, old_str="def foo():\n    return 42\n")
    assert r["success"] is True
    with open(sample_file) as f:
        assert "foo" not in f.read()


@pytest.mark.asyncio
async def test_unknown_action(editor, sample_file):
    r = await editor.execute(action="invalid_xyz", path=sample_file)
    assert r["success"] is False


@pytest.mark.asyncio
async def test_file_not_found(editor):
    r = await editor.execute(action="view_lines", path="/tmp/nonexistent_xyz_file.py")
    assert r["success"] is False
