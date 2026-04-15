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
            response = await self.router.generate(
                messages=messages,
                task_hint="think"
            )
            
            # Extract JSON from response
            from backend.utils.json_repair import repair_and_parse
            from backend.utils.tool_schemas import PlanSchema

            text = response.get("text", "")
            plan_json = None
            parse_attempts = 0
            max_parse_attempts = 3

            while parse_attempts < max_parse_attempts and plan_json is None:
                parsed, err = repair_and_parse(text)

                if parsed and isinstance(parsed, dict):
                    # Validate with Pydantic
                    try:
                        validated_plan = PlanSchema(**parsed)
                        plan_json = validated_plan.model_dump()
                    except Exception as ve:
                        logger.warning(
                            f"Plan schema validation failed: {ve}. "
                            f"Attempt {parse_attempts+1}"
                        )
                        plan_json = None

                if plan_json is None and parse_attempts < max_parse_attempts - 1:
                    # Ask model to fix its output
                    fix_messages = messages + [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": (
                                "Your response was not valid JSON. "
                                "Output ONLY the JSON object with "
                                '"strategy" and "phases" keys. '
                                "No explanation, no markdown, pure JSON."
                            )
                        }
                    ]
                    fix_response = await self.router.generate(
                        messages=fix_messages, task_hint="think"
                    )
                    text = fix_response.get("text", "")

                parse_attempts += 1

            if plan_json and plan_json.get("phases"):
                state.current_plan = plan_json
                from backend.utils.structured_logger import log_plan
                log_plan(
                    state.session_id,
                    plan_json,
                    state.task_description
                )
                await self.log_thought(
                    f"Plan created: {len(plan_json.get('phases',[]))} phases.",
                    websocket_send
                )
            else:
                raise ValueError(
                    f"Could not get valid JSON plan after "
                    f"{max_parse_attempts} attempts."
                )
                
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
