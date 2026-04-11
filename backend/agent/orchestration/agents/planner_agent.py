import json
import logging
from typing import Optional, Callable, List, Dict, Any
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """
    Responsible for analyzing user tasks and decomposing them into a structured plan.
    """
    def __init__(self, router: ModelRouter):
        super().__init__("Planner", router)

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        await self.log_info(f"Analyzing task and creating execution plan...", websocket_send)
        
        # System prompt for planning
        system_prompt = """
        You are the Planner Agent for Archimedes.
        Your goal is to take a user task and decompose it into a sequence of actionable phases.
        
        OUTPUT FORMAT:
        You must output ONLY a valid JSON object.
        LANGUAGE: All descriptions and text MUST BE IN RUSSIAN.
        JSON Structure:
        {
            "strategy": "sequential" | "parallel",
            "phases": [
                {
                    "title": "Phase title",
                    "subtasks": [
                        {"type": "execute", "description": "Description of subtask", "params": {}},
                        ...
                    ]
                }
            ]
        }
        
        SUBTASK TYPES:
        - execute: General task execution (research, coding, analysis).
        - browser: specifically for complex web navigation or scraping.
        - slides: specifically for presentation generation.
        - verify: specifically for final quality checks.
        
        Be concise but thorough. Focus on logic and dependencies. 
        IMPORTANT: Use RUSSIAN language for all descriptions.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {state.task_description}"}
        ]
        
        try:
            response = await self.router.generate(
                messages=messages,
                task_hint="think"
            )
            
            # Extract JSON from response
            text = response.get("text", "")
            
            # More robust JSON extraction
            import re
            json_match = re.search(r"(\{.*\})", text, re.DOTALL)
            plan_json = None
            
            if json_match:
                json_str = json_match.group(1).strip()
                try:
                    plan_json = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try cleaning common LLM artifacts (like trailing commas or excessive whitespace)
                    try:
                        # Clean trailing commas before closing braces/brackets
                        clean_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                        plan_json = json.loads(clean_str)
                    except:
                        pass
            
            if plan_json:
                state.current_plan = plan_json
                await self.log_thought(f"Created plan with {len(plan_json.get('phases', []))} phases.", websocket_send)
            else:
                raise ValueError(f"Model failed to output valid JSON plan. Raw text: {text[:200]}...")
                
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            await self.log_info(f"Warning: Falling back to single-phase plan due to error: {e}", websocket_send)
            # Fallback plan
            state.current_plan = {
                "strategy": "sequential",
                "phases": [
                    {
                        "title": "Action Phase",
                        "subtasks": [{"type": "execute", "description": state.task_description, "params": {}}]
                    }
                ]
            }
            
        return state
