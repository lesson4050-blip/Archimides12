"""Tests for ASTTool (test 1.18)."""
import os
import pytest
from backend.tools.ast_tool import ASTTool


@pytest.fixture
def tool():
    return ASTTool()


@pytest.fixture
def py_file(tmp_path):
    code = '''import os
from typing import List

class MyClass:
    """A sample class."""
    def method_a(self, x: int) -> int:
        return x + 1

    def method_b(self):
        return os.getcwd()

def standalone_func(items: List[str]) -> str:
    return ", ".join(items)

def helper():
    return MyClass().method_a(5)
'''
    p = tmp_path / "sample.py"
    p.write_text(code)
    return str(p)


@pytest.mark.asyncio
async def test_outline(tool, py_file):
    r = await tool.execute(session_id="t", action="outline", path=py_file)
    assert r["success"] is True
    assert len(r["classes"]) == 1
    assert r["classes"][0]["name"] == "MyClass"
    assert len(r["functions"]) >= 2


@pytest.mark.asyncio
async def test_find_class(tool, py_file):
    r = await tool.execute(session_id="t", action="find_class", path=py_file, target="MyClass")
    assert r["success"] is True
    assert r["found"] is True
    assert "method_a" in r["methods"]


@pytest.mark.asyncio
async def test_find_class_not_found(tool, py_file):
    r = await tool.execute(session_id="t", action="find_class", path=py_file, target="NonExistent")
    assert r["success"] is True
    assert r["found"] is False


@pytest.mark.asyncio
async def test_find_function(tool, py_file):
    r = await tool.execute(session_id="t", action="find_function", path=py_file, target="standalone_func")
    assert r["success"] is True
    assert r["found"] is True


@pytest.mark.asyncio
async def test_get_imports(tool, py_file):
    r = await tool.execute(session_id="t", action="get_imports", path=py_file)
    assert r["success"] is True
    modules = [i["module"] for i in r["imports"]]
    assert "os" in modules


@pytest.mark.asyncio
async def test_dependency_graph(tool, py_file):
    r = await tool.execute(session_id="t", action="dependency_graph", path=py_file)
    assert r["success"] is True
    assert "graph" in r


@pytest.mark.asyncio
async def test_dependency_graph_target(tool, py_file):
    r = await tool.execute(session_id="t", action="dependency_graph", path=py_file, target="helper")
    assert r["success"] is True
    assert r["target"] == "helper"


@pytest.mark.asyncio
async def test_add_import(tool, py_file):
    r = await tool.execute(session_id="t", action="add_import", path=py_file, new_code="import json")
    assert r["success"] is True
    with open(py_file) as f:
        assert "import json" in f.read()


@pytest.mark.asyncio
async def test_replace_function(tool, py_file):
    new = "def standalone_func(items):\n    return str(items)"
    r = await tool.execute(session_id="t", action="replace_function", path=py_file, target="standalone_func", new_code=new)
    assert r["success"] is True
    with open(py_file) as f:
        assert "str(items)" in f.read()


@pytest.mark.asyncio
async def test_invalid_path(tool):
    r = await tool.execute(session_id="t", action="outline", path="/nonexistent.py")
    assert r["success"] is False


@pytest.mark.asyncio
async def test_unknown_action(tool, py_file):
    r = await tool.execute(session_id="t", action="invalid_xyz", path=py_file)
    assert r["success"] is False
