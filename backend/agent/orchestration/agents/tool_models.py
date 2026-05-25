from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union, Tuple

class FileToolModel(BaseModel):
    action: str = Field(..., description="Action to perform: 'read', 'write', 'append', 'edit', 'view', 'delete', 'list', 'exists'")
    path: str = Field(..., description="Path to the file or directory")
    content: Optional[str] = Field(None, description="Content to write or append")
    encoding: Optional[str] = Field("utf-8", description="File encoding")
    start_line: Optional[int] = Field(None, description="Start line number for read or edit")
    end_line: Optional[int] = Field(None, description="End line number for read or edit")
    old_string: Optional[str] = Field(None, description="Deprecated: string to replace (for edit)")
    new_string: Optional[str] = Field(None, description="Deprecated: replacement string (for edit)")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = ['read', 'write', 'append', 'edit', 'view', 'delete', 'list', 'exists']
        if v not in allowed:
            raise ValueError(f"Action must be one of {allowed}")
        return v

class ShellToolModel(BaseModel):
    command: str = Field(..., description="The shell command to execute")
    timeout: Optional[int] = Field(60, description="Command timeout in seconds")

class SearchToolModel(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: Optional[int] = Field(5, description="Maximum number of results to return")
    search_depth: Optional[str] = Field("basic", description="basic, advanced, or neural")
    multi_hop: Optional[bool] = Field(False, description="Enable iterative multi-hop search")

class CanvasEngineToolModel(BaseModel):
    topic: str = Field(..., description="Presentation topic")
    slides_json: str = Field(..., description="JSON array of slide objects [{title, body, notes}]")

class BrowserToolModel(BaseModel):
    action: str = Field(..., description="Action: 'navigate', 'click', 'type', 'screenshot', 'extract'")
    url: Optional[str] = Field(None, description="URL for 'navigate'")
    selector: Optional[str] = Field(None, description="CSS selector for 'click' or 'type'")
    value: Optional[str] = Field(None, description="Value for 'type'")

# Registry of models for easy lookup
TOOL_MODELS = {
    "file": FileToolModel,
    "shell": ShellToolModel,
    "search": SearchToolModel,
    "canvas_engine": CanvasEngineToolModel,
    "browser": BrowserToolModel
}

def validate_tool_call(name: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates tool parameters against the Pydantic model.
    Returns (is_valid, error_message).
    """
    model = TOOL_MODELS.get(name)
    if not model:
        # If no model defined, we pass it through (soft migration)
        return True, None
    
    try:
        model(**params)
        return True, None
    except Exception as e:
        return False, str(e)
