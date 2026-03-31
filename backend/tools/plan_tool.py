from typing import List, Dict, Any, Optional
from backend.agent.planner import PlanManager

class PlanTool:
    """
    Manages the task plan.
    """
    def __init__(self, plan_manager: PlanManager):
        self.plan_manager = plan_manager

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "plan",
                "description": "Manages the task execution plan.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["update", "advance", "create_plan"]},
                        "phases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            },
                            "description": "List of phases (for update/create_plan)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, phases: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:
        if action in ("update", "create_plan"):
            if not phases:
                # If content is provided instead of phases (ollama style)
                content = kwargs.get("content")
                if content:
                    phases = [{"title": "Main Phase", "description": content}]
                else:
                    return {"success": False, "error": "Phases or content required for 'update/create_plan'."}
            self.plan_manager.update_plan(phases)
            return {"success": True, "output": f"Plan updated with {len(phases)} phases."}
            
        elif action == "advance":
            success = self.plan_manager.advance_phase()
            if success:
                return {"success": True, "output": "Advanced to next phase."}
            else:
                return {"success": False, "error": "Already at the last phase or no plan exists."}
                
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
