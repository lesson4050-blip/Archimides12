import logging
import re
from typing import Optional, Callable, Dict, Any
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.agent.orchestration.agents.planner_agent import PlannerAgent
from backend.agent.orchestration.agents.executor_agent import ExecutorAgent
from backend.agent.orchestration.agents.critic_agent import CriticAgent
from backend.models.model_router import ModelRouter
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

logger = logging.getLogger(__name__)

# Simple patterns that don't need planning or critic review
CONVERSATIONAL_PATTERNS = [
    r"^(привет|здравствуй|хай|hi|hello|hey|добрый\s+(день|вечер|утро))[\s!.?]*$",
    r"^(как\s+дела|что\s+ты\s+умеешь|кто\s+ты|что\s+ты\s+такое|помо(щь|ги))[\s!.?]*$",
    r"^(спасибо|пока|до\s+свидания|bye|thanks|thank\s+you)[\s!.?]*$",
]

def is_conversational(text: str) -> bool:
    """Check if the task is a simple conversational message (greeting, etc.)."""
    cleaned = text.strip().lower()
    # Very short messages are likely conversational
    if len(cleaned) < 15 and not any(c in cleaned for c in ["/", "\\", "{", "}", "http"]):
        for pattern in CONVERSATIONAL_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return True
    return False

COMPLEX_KEYWORDS = [
    "create", "build", "write code", "implement", "analyze",
    "research", "find all", "compare", "generate report",
    "make a presentation", "deploy", "setup", "configure",
    "create website", "scrape", "automate",
    "создай", "напиши код", "проанализируй", "исследуй",
    "сделай сайт", "автоматизируй", "скрапь", "разработай",
]

def classify_task(text: str) -> str:
    text_lower = text.lower().strip()
    if len(text_lower) < 20:
        return "simple"
    if any(kw in text_lower for kw in COMPLEX_KEYWORDS):
        return "complex"
    if len(text_lower) < 80:
        return "medium"
    return "complex"


class AgentOrchestrator:
    """
    Coordinates the multi-agent flow: Planner -> Executor -> Critic.
    Also handles the 'Fast' mode vs 'Planning' mode logic.
    """
    def __init__(self, 
                 router: ModelRouter, 
                 tool_registry: ToolRegistry, 
                 context_manager: ContextManager):
        self.router = router
        self.planner = PlannerAgent(router)
        self.executor = ExecutorAgent(router, tool_registry, context_manager)
        self.critic = CriticAgent(router)
        from backend.agent.orchestration.swarm import MicroAgentSwarm
        self.swarm = MicroAgentSwarm(router)
        
    async def run_task(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None,
                       task_hint: str = "default") -> Dict[str, Any]:
        
        # Initialize state
        state = OrchestrationState(
            session_id=session_id,
            task_description=task_description,
            mode=mode,
            task_hint=task_hint
        )
        
        # Add initial greeting/task to history
        state.add_message("user", task_description)
        
        # Shortcut: conversational messages get answered directly without planning/critic
        if is_conversational(task_description):
            logger.info(f"[{session_id}] Detected conversational message, using direct response")
            return await self._run_conversational(state, websocket_send)
        
        complexity = classify_task(task_description)
        if complexity == "simple" and mode != AgentMode.FAST:
            logger.info(f"[{session_id}] Simple task → fast mode")
            return await self._run_fast_mode(state, websocket_send)
        
        if mode == AgentMode.FAST:
            return await self._run_fast_mode(state, websocket_send)
        else:
            return await self._run_planning_mode(state, websocket_send)

    async def _run_conversational(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Direct LLM response for simple conversational messages — no tools, no critic."""
        logger.info(f"[{state.session_id}] Orchestrator: conversational shortcut")
        
        messages = [
            {"role": "system", "content": "Ты — Archimedes, дружелюбный и профессиональный AI-ассистент. Отвечай на русском языке. Будь кратким и приветливым."},
            {"role": "user", "content": state.task_description}
        ]
        
        try:
            response = await self.router.generate(messages=messages, task_hint="think")
            result_text = response.get("text", "Привет! Чем могу помочь?")
            
            state.results.append({"step": 0, "output": result_text})
            return await self._get_final_response(state, websocket_send)
        except Exception as e:
            logger.error(f"Conversational response failed: {e}")
            fallback = "Привет! Я Archimedes — ваш AI-ассистент. Чем могу помочь?"
            state.results.append({"step": 0, "output": fallback})
            return await self._get_final_response(state, websocket_send)

    async def _run_fast_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering FAST mode")
        state = await self.executor.process(state, websocket_send)
        return await self._get_final_response(state, websocket_send)

    async def _run_planning_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering PLANNING mode")
        
        # 1. PLAN
        state = await self.planner.process(state, websocket_send)
        if not state.current_plan:
             return {"success": False, "error": "Planning failed and fallback failed."}
        
        # 2. EXECUTE & CRITIQUE LOOP
        # Flatten subtasks for easier iteration
        all_subtasks = []
        for phase in state.current_plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                all_subtasks.append(subtask)
        
        for i, subtask in enumerate(all_subtasks):
            state.current_step_index = i
            
            # Subtask loop (includes critic retries)
            while True:
                current_target = subtask.get("description", state.task_description)
                # EXECUTE
                # Use swarm for complex subtasks
                if state.task_hint in ("execute", "search") or len(all_subtasks) > 2:
                    swarm_result = await self.swarm.run(
                        task=current_target,
                        task_hint=state.task_hint,
                        websocket_send=websocket_send
                    )
                    state.results.append({
                        "step": i,
                        "output": swarm_result
                    })
                    # Still run critic on swarm output
                    state = await self.critic.process(state, websocket_send)
                else:
                    state = await self.executor.process(state, websocket_send)
                    state = await self.critic.process(state, websocket_send)
                
                verdict = state.metadata.get("critic_verdict")
                
                if verdict == "PASS" or verdict == "LIMIT_REACHED" or verdict == "ERROR_BYPASS":
                    # Subtask successful or best effort reached
                    break
                elif verdict == "RETRY":
                    # Continue loop to re-execute with critic feedback
                    continue
                else:
                    # Unexpected state, break to avoid infinite loop
                    break
                    
        return await self._get_final_response(state, websocket_send)

    async def _get_final_response(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Synthesize final output from results."""
        if not state.results:
            return {"success": False, "error": "No results generated."}
        
        # Fast mode: Just return the last result
        if state.mode == AgentMode.FAST or len(state.results) == 1:
            final_output = state.results[-1].get("output", "Done.")
        else:
            # Planning mode: Synthesize all steps into a cohesive response
            if websocket_send:
                await websocket_send({"type": "info", "content": "Синтезирую итоговый ответ..."})
            
            summary_prompt = "На основе результатов всех выполненных подзадач сформируй итоговый ответ пользователю на его изначальный запрос.\n\n"
            summary_prompt += f"ИЗНАЧАЛЬНЫЙ ЗАПРОС: {state.task_description}\n\n"
            for res in state.results:
                summary_prompt += f"Шаг {res.get('step')}: {res.get('output')}\n"
            
            try:
                response = await self.router.generate(
                    messages=[{"role": "user", "content": summary_prompt}],
                    task_hint="think"
                )
                final_output = response.get("text", state.results[-1].get("output", "Done."))
            except Exception as e:
                logger.error(f"Failed to synthesize final response: {e}")
                final_output = state.results[-1].get("output", "Done.")

        return {
            "success": True,
            "output": final_output,
            "history": state.history,
            "plan": state.current_plan,
            "mode": state.mode.value
        }

