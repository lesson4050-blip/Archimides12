from typing import Dict, Any

class BaseTool:
    """Base class for all Archimedes tools."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def get_definition(self) -> Dict[str, Any]:
        """Returns the OpenAI-format tool definition."""
        raise NotImplementedError

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Executes the tool action."""
        raise NotImplementedError
