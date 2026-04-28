"""Tests for JSON repair utility (test 1.13)."""
import pytest
from backend.utils.json_repair import repair_and_parse


def test_repair_valid_json():
    result, err = repair_and_parse('{"key": "value"}')
    assert result == {"key": "value"}
    assert err == ""


def test_repair_empty_input():
    result, err = repair_and_parse("")
    assert result is None
    assert "Empty" in err


def test_repair_json_in_markdown():
    raw = '```json\n{"tool": "shell"}\n```'
    result, err = repair_and_parse(raw)
    assert result == {"tool": "shell"}


def test_repair_trailing_comma():
    raw = '{"a": 1, "b": 2,}'
    result, err = repair_and_parse(raw)
    assert result is not None
    assert result["a"] == 1


def test_repair_truncated():
    raw = '{"name": "test", "items": [1, 2, 3'
    result, err = repair_and_parse(raw)
    assert result is not None
    assert result["name"] == "test"


def test_repair_single_quotes():
    raw = "{'name': 'value'}"
    result, err = repair_and_parse(raw)
    assert result is not None


def test_repair_surrounded_by_text():
    raw = 'Answer: {"action": "search"} done.'
    result, err = repair_and_parse(raw)
    assert result is not None
    assert result["action"] == "search"


def test_repair_array():
    result, err = repair_and_parse('[1, 2, 3]')
    assert result == [1, 2, 3]


def test_repair_broken():
    result, err = repair_and_parse("not json")
    assert result is None
