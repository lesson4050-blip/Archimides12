import logging
from typing import Optional, Callable
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter
from backend.agent.llm_router import llm_router, OutputMode
from pydantic import BaseModel
from typing import List, Dict, Any

class _SubTask(BaseModel):
    type: str = "execute"
    description: str
    params: Dict[str, Any] = {}

class _Phase(BaseModel):
    title: str
    subtasks: List[_SubTask] = []

class _PlanResponse(BaseModel):
    strategy: str = "sequential"
    phases: List[_Phase] = []


logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """
    Responsible for analyzing user tasks and decomposing them into a structured plan.
    """
    def __init__(self, router: ModelRouter):
        super().__init__("Planner", router)

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        await self.log_info("Analyzing task and creating execution plan...", websocket_send)
        
        # System prompt for planning
        system_prompt = """
        You are the Planner Agent for Archimedes.
        Your goal is to take a user task and decompose it into a sequence of actionable phases.
        
        OUTPUT FORMAT:
        You must output ONLY a valid JSON object.
        LANGUAGE: All descriptions and text MUST BE IN RUSSIAN.
        JSON Structure:
        {{
            "strategy": "sequential" | "parallel",
            "phases": [
                {{
                    "title": "Phase title",
                    "subtasks": [
                        {{"type": "execute", "description": "Description of subtask", "params": {{}}}},
                        ...
                    ]
                }}
            ]
        }}
        
        SUBTASK TYPES:
        - execute: General task execution (research, coding, analysis).
        - browser: specifically for complex web navigation or scraping.
        - slides: specifically for presentation generation.
        - verify: specifically for final quality checks.
        
        Be concise but thorough. Focus on logic and dependencies. 
        IMPORTANT: Use RUSSIAN language for all descriptions.
        
        STEERING DIRECTIVES:
        - Mode: {task_hint}
        {hint_instructions}
        """
        
        hint_instructions = ""
        if state.task_hint == "search":
            hint_instructions = "- MISSION: Deep research. Include multiple search steps, source cross-referencing, and a comprehensive summary phase."
        elif state.task_hint == "plan":
            hint_instructions = "- MISSION: Presentation. Include steps for outline creation, content generation per slide, and visual formatting."
        elif state.task_hint == "execute":
            hint_instructions = "- MISSION: Technical implementation. Focus on direct tool usage (shell, file) and verification."
        
        formatted_prompt = system_prompt.format(
            task_hint=state.task_hint,
            hint_instructions=hint_instructions
        )
        
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": f"Task: {state.task_description}"}
        ]
        
        try:
            plan_obj = await llm_router.call(
                messages=messages,
                mode=OutputMode.STRICT_JSON,
                response_model=_PlanResponse,
                task_hint="think",
                max_retries=3
            )
            plan_json = plan_obj.model_dump()
            state.current_plan = plan_json
            
            from backend.utils.structured_logger import log_plan
            log_plan(
                state.session_id,
                plan_json,
                state.task_description
            )
            
            await self.log_thought(
                f"Plan: {len(plan_json.get('phases',[]))} phases "
                f"(grammar-constrained JSON)",
                websocket_send
            )
        except Exception as e:
            logger.error(f"Planning failed even with grammar constraint: {e}")
            await self.log_info(f"Warning: Falling back to single-phase plan due to error: {e}", websocket_send)
            state.current_plan = {
                "strategy": "sequential",
                "phases": [{"title": "Action Phase", "subtasks": [
                    {"type": "execute", "description": state.task_description,
                     "params": {}}
                ]}]
            }

        return state
