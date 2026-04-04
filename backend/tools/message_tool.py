from typing import List, Dict, Any, Optional

class MessageTool:
    """
    Handles communication with the user.
    """
    async def execute(self, action: str = "result", text: Optional[str] = None, content: Optional[str] = None, attachments: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "type": action, 
            "text": text or content or "",
            "attachments": attachments or []
        }
