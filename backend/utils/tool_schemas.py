"""
Pydantic validation schemas for tool call parameters.
Every tool call is validated before execution.
"""
from pydantic import BaseModel, field_validator
from typing import Any, Dict, Optional, Literal
import re


class ToolCallSchema(BaseModel):
    name: str
    params: Dict[str, Any] = {}

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Tool name must be a non-empty string")
        # Remove any accidental formatting
        v = v.strip().strip('"').strip("'")
        return v

    @field_validator('params')
    @classmethod
    def params_must_be_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, str):
            from backend.utils.json_repair import repair_and_parse
            parsed, err = repair_and_parse(v)
            if parsed and isinstance(parsed, dict):
                return parsed
            return {}
        if not isinstance(v, dict):
            return {}
        return v


class PlanSchema(BaseModel):
    strategy: Literal["sequential", "parallel"] = "sequential"
    phases: list = []

    @field_validator('phases')
    @classmethod
    def phases_must_be_list(cls, v):
        if not isinstance(v, list):
            return []
        return v


def validate_tool_call(raw_tool_call: Any) -> Optional[ToolCallSchema]:
    """
    Validate and normalize a tool call from any model.
    Returns None if invalid beyond repair.
    """
    if raw_tool_call is None:
        return None
    try:
        if isinstance(raw_tool_call, dict):
            return ToolCallSchema(**raw_tool_call)
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Tool call validation failed: {e}. Raw: {raw_tool_call}"
        )
        return None


def fuzzy_match_tool_name(name: str, available_tools: list) -> Optional[str]:
    """
    If the model hallucinates a slightly wrong tool name,
    try to find the closest match.
    Examples: 'shell_exec' -> 'shell', 'browser_navigate' -> 'browser'
    """
    if name in available_tools:
        return name

    name_lower = name.lower().replace('-', '_').replace(' ', '_')

    # Direct match after normalization
    for tool in available_tools:
        if tool.lower() == name_lower:
            return tool

    # Prefix match: model called 'shell_exec', we have 'shell'
    for tool in available_tools:
        if name_lower.startswith(tool.lower()) or tool.lower().startswith(name_lower):
            return tool

    # Contains match
    for tool in available_tools:
        if tool.lower() in name_lower or name_lower in tool.lower():
            return tool

    return None
