import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AgentNode:
    """
    Hierarchical Swarm Orchestrator (Phase 8).
    Spawns and manages child agents to execute sub-tasks in parallel.
    Tensor-to-Tensor (T2T) via EventBus.
    """
    def __init__(self, executor_agent):
        self.parent = executor_agent

    async def spawn_agent(self, role: str, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Spawns a child agent instance asynchronously.
        """
        logger.info(f"Spawning child AgentNode [Role: {role}] for task: {task[:50]}...")
        
        from backend.agent.orchestration.state import OrchestrationState, AgentMode
        
        # Fix: get session_id safely
        session_id = getattr(self.parent, 'session_id', None) or "swarm-default"
        
        child_state = OrchestrationState(
            session_id=f"{session_id}-{role}",
            task_description=f"[{role.upper()}] {task}",
            mode=AgentMode.FAST
        )
        
        if context:
            for k, v in context.items():
                child_state.metadata[k] = v
        
        try:
            result_state = await self.parent.process(child_state)
            
            output_history = [res.get("output", "") for res in result_state.results]
            final_output = "\n".join(output_history[-3:]) if output_history else "No output."
            
            # Fix: use async emit instead of sync publish
            if hasattr(self.parent, "event_bus") and self.parent.event_bus:
                try:
                    await self.parent.event_bus.emit_progress(
                        session_id=session_id,
                        step=f"swarm_{role}_complete",
                        data={"role": role, "output_preview": final_output[:100]}
                    )
                except Exception:
                    pass  # EventBus failure must not kill swarm
            
            return {
                "success": True,
                "role": role,
                "output": final_output,
                "confidence": getattr(result_state, "confidence_score", 100)
            }
        except Exception as e:
            logger.error(f"AgentNode swarm spawn failed for {role}: {e}")
            return {"success": False, "role": role, "error": str(e)}
