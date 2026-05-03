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
        
        # We create a new state for the child
        from backend.agent.orchestration.state import OrchestrationState, AgentMode
        child_state = OrchestrationState(
            session_id=self.parent.context_manager.session_id,
            task_description=f"[{role.upper()}] {task}",
            mode=AgentMode.FAST
        )
        
        # Inject context into the child's memory
        if context:
            for k, v in context.items():
                child_state.metadata[k] = v

        # Execute the child agent process
        try:
            # We run process in a separate task but await it for the result
            # For true parallel swarm, we'd fire & forget and listen to event_bus,
            # but returning the output is cleaner for tool calls.
            result_state = await self.parent.process(child_state)
            
            output_history = [res.get("output", "") for res in result_state.results]
            final_output = "\n".join(output_history[-3:]) if output_history else "No output generated."
            
            # Broadcast success via EventBus (T2T communication)
            if hasattr(self.parent, "event_bus") and self.parent.event_bus:
                self.parent.event_bus.publish("swarm_sync", {
                    "role": role,
                    "task": task,
                    "status": "completed",
                    "output_preview": final_output[:100]
                })

            return {
                "success": True,
                "role": role,
                "output": final_output,
                "confidence": getattr(result_state, "confidence_score", 100)
            }
        except Exception as e:
            logger.error(f"AgentNode swarm spawn failed for {role}: {e}")
            return {
                "success": False,
                "role": role,
                "error": str(e)
            }
