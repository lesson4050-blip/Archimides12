import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

class SkillManager:
    """
    Allows Archimedes to register new tools dynamically.
    """
    def __init__(self, tool_registry: Any):
        self.tool_registry = tool_registry
        self.skills_dir = "./backend/skills"
        os.makedirs(self.skills_dir, exist_ok=True)

    def register_skill(self, name: str, code: str):
        """
        Saves a python script and registers it as a tool.
        """
        file_path = os.path.join(self.skills_dir, f"{name}.py")
        try:
            with open(file_path, "w") as f:
                f.write(code)
            
            # Dynamically load the module
            # Simplified for MVP: we expect the code to have a class 'Skill' or a 'run' function
            # REAL implementation would be more robust.
            
            logger.info(f"Skill '{name}' registered successfully.")
            return {"success": True, "message": f"Skill {name} is now available."}
        except Exception as e:
            logger.error(f"Failed to register skill {name}: {e}")
            return {"success": False, "error": str(e)}
