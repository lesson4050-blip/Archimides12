"""
Pydantic validation schemas for tool call parameters.

v2 upgrades:
- Per-tool parameter schemas (shell, file, ast_navigator, fast_linter)
- Strict type coercion for local model mistakes
- Auto-repair of common hallucinated parameter names
- Validation metrics tracking
"""
from pydantic import BaseModel, field_validator, model_validator
from typing import Any, Dict, List, Optional, Literal, Union
import logging

logger = logging.getLogger(__name__)

# ─── Validation metrics ──────────────────────────────────────────

_validation_stats = {
    "total": 0,
    "passed": 0,
    "repaired": 0,
    "rejected": 0,
}


def get_validation_stats() -> Dict[str, int]:
    return dict(_validation_stats)


# ─── Per-tool parameter schemas ─────────────────────────────────

class ShellParams(BaseModel):
    action: Literal["exec", "run", "view", "wait", "kill"] = "exec"
    command: Optional[str] = None
    timeout: Optional[int] = 60
    pid: Optional[int] = None
    seconds: Optional[int] = None

    @field_validator('action', mode='before')
    @classmethod
    def normalize_action(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            # Common hallucinations
            if v in ("execute", "run_command", "bash", "sh"):
                return "exec"
        return v

    @field_validator('timeout', mode='before')
    @classmethod
    def coerce_timeout(cls, v):
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return 60
        return v


class FileParams(BaseModel):
    action: Literal["read", "write", "append", "edit", "view"] = "read"
    path: str
    content: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    old_string: Optional[str] = None
    new_string: Optional[str] = None

    @field_validator('action', mode='before')
    @classmethod
    def normalize_action(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ("create", "save", "put"):
                return "write"
            if v in ("open", "get", "cat"):
                return "read"
            if v in ("modify", "patch", "update", "replace"):
                return "edit"
            if v in ("ls", "list", "dir"):
                return "view"
        return v

    @field_validator('start_line', 'end_line', mode='before')
    @classmethod
    def coerce_line_numbers(cls, v):
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return None
        return v


class ASTParams(BaseModel):
    action: Literal[
        "find_class", "find_function", "get_imports",
        "outline", "replace_function", "replace_class",
        "add_import", "dependency_graph"
    ]
    path: str
    target: Optional[str] = None
    new_code: Optional[str] = None


class FastLinterParams(BaseModel):
    action: Literal["lint_file", "lint_code"] = "lint_file"
    path: Optional[str] = None
    code: Optional[str] = None


class SearchParams(BaseModel):
    query: str
    num_results: Optional[int] = 5


# ─── Registry of per-tool schemas ────────────────────────────────

TOOL_PARAM_SCHEMAS: Dict[str, type] = {
    "shell": ShellParams,
    "file": FileParams,
    "ast_navigator": ASTParams,
    "fast_linter": FastLinterParams,
    "search": SearchParams,
}


# ─── Common hallucinated parameter name aliases ─────────────────

PARAM_ALIASES = {
    # Model says → we correct to
    "cmd": "command",
    "bash": "command",
    "script": "command",
    "filepath": "path",
    "file_path": "path",
    "filename": "path",
    "file": "path",
    "text": "content",
    "body": "content",
    "data": "content",
    "source": "content",
    "q": "query",
    "search_query": "query",
    "question": "query",
    "name": "target",
    "class_name": "target",
    "function_name": "target",
    "func_name": "target",
    "replacement": "new_code",
    "new_content": "new_code",
    "replacement_code": "new_code",
    "start": "start_line",
    "end": "end_line",
    "line_start": "start_line",
    "line_end": "end_line",
}


# ─── Main validation schemas ────────────────────────────────────

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

    @model_validator(mode='after')
    def fix_param_aliases(self):
        """Auto-repair hallucinated parameter names."""
        fixed = {}
        repaired_any = False
        for key, val in self.params.items():
            canonical = PARAM_ALIASES.get(key, key)
            if canonical != key:
                repaired_any = True
                logger.debug(f"Param alias: '{key}' → '{canonical}'")
            fixed[canonical] = val
        
        if repaired_any:
            self.params = fixed
            _validation_stats["repaired"] += 1
        
        return self


class PlanSchema(BaseModel):
    strategy: Literal["sequential", "parallel"] = "sequential"
    phases: list = []

    @field_validator('phases')
    @classmethod
    def phases_must_be_list(cls, v):
        if not isinstance(v, list):
            return []
        return v


# ─── Public API ──────────────────────────────────────────────────

def validate_tool_call(raw_tool_call: Any) -> Optional[ToolCallSchema]:
    """
    Validate and normalize a tool call from any model.
    
    Flow:
    1. Parse into ToolCallSchema (fixes aliases, coerces params)
    2. If a per-tool schema exists, validate params against it
    3. Returns validated schema or None if beyond repair
    """
    _validation_stats["total"] += 1

    if raw_tool_call is None:
        return None
    try:
        if isinstance(raw_tool_call, dict):
            schema = ToolCallSchema(**raw_tool_call)
            
            # Per-tool validation
            tool_schema_cls = TOOL_PARAM_SCHEMAS.get(schema.name)
            if tool_schema_cls:
                try:
                    validated = tool_schema_cls(**schema.params)
                    # Write back validated (and coerced) params
                    schema.params = validated.model_dump(exclude_none=True)
                except Exception as e:
                    logger.warning(
                        f"Per-tool validation for '{schema.name}' failed: {e}. "
                        f"Using raw params."
                    )
            
            _validation_stats["passed"] += 1
            return schema
        
        return None
    except Exception as e:
        _validation_stats["rejected"] += 1
        logger.warning(
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
