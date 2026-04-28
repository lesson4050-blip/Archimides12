"""Tests for tool_schemas validation (test 1.14)."""
import pytest
from backend.utils.tool_schemas import (
    validate_tool_call, fuzzy_match_tool_name,
    ShellParams, FileParams, ASTParams,
    ToolCallSchema, PARAM_ALIASES,
)


def test_validate_valid_shell():
    tc = validate_tool_call({"name": "shell", "params": {"command": "ls"}})
    assert tc is not None
    assert tc.name == "shell"
    assert tc.params["command"] == "ls"


def test_validate_shell_action_alias():
    tc = validate_tool_call({"name": "shell", "params": {"action": "execute", "command": "ls"}})
    assert tc is not None
    assert tc.params["action"] == "exec"


def test_validate_param_alias_cmd():
    tc = validate_tool_call({"name": "shell", "params": {"cmd": "ls -la"}})
    assert tc is not None
    assert tc.params.get("command") == "ls -la"


def test_validate_file_action_alias():
    tc = validate_tool_call({"name": "file", "params": {"action": "create", "path": "/tmp/x.py"}})
    assert tc is not None
    assert tc.params["action"] == "write"


def test_validate_none_input():
    assert validate_tool_call(None) is None


def test_validate_empty_name():
    assert validate_tool_call({"name": "", "params": {}}) is None


def test_fuzzy_match_exact():
    tools = ["shell", "file", "search"]
    assert fuzzy_match_tool_name("shell", tools) == "shell"


def test_fuzzy_match_prefix():
    tools = ["shell", "file", "browser"]
    assert fuzzy_match_tool_name("shell_exec", tools) == "shell"


def test_fuzzy_match_none():
    tools = ["shell", "file"]
    assert fuzzy_match_tool_name("xyzzy", tools) is None


def test_shell_params_timeout_coerce():
    p = ShellParams(command="ls", timeout="30")
    assert p.timeout == 30


def test_file_params_line_coerce():
    p = FileParams(path="/tmp/x.py", start_line="10", end_line="20")
    assert p.start_line == 10
    assert p.end_line == 20
