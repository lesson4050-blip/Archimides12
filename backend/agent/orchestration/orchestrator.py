import logging
from typing import Optional, Callable, Dict, Any
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.agent.orchestration.agents.planner_agent import PlannerAgent
from backend.agent.orchestration.agents.executor_agent import ExecutorAgent
from backend.agent.orchestration.agents.critic_agent import CriticAgent
from backend.models.model_router import ModelRouter
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

logger = logging.getLogger(__name__)

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
        
    async def run_task(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        
        # Initialize state
        state = OrchestrationState(
            session_id=session_id,
            task_description=task_description,
            mode=mode
        )
        
        # Add initial greeting/task to history
        state.add_message("user", task_description)
        
        if mode == AgentMode.FAST:
            return await self._run_fast_mode(state, websocket_send)
        else:
            return await self._run_planning_mode(state, websocket_send)

    async def _run_fast_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering FAST mode")
        state = await self.executor.process(state, websocket_send)
        return self._get_final_response(state)

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
                # EXECUTE
                state = await self.executor.process(state, websocket_send)
                
                # CRITIQUE (only if configured to review, or default to review everything in planning mode)
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
                    
        return self._get_final_response(state)

    def _get_final_response(self, state: OrchestrationState) -> Dict[str, Any]:
        """Synthesize final output from results."""
        if not state.results:
            return {"success": False, "error": "No results generated."}
        
        # Final result is typically the last one
        final_output = state.results[-1].get("output", "Done.")
        return {
            "success": True,
            "output": final_output,
            "history": state.history,
            "plan": state.current_plan,
            "mode": state.mode.value
        }
