"""
Phase 8 — Shift 2: Hierarchical Swarm Orchestration (Devin-killer).
Spawns parallel child agents for different roles (frontend, backend, tests).
The parent ExecutorAgent becomes a Manager that delegates sub-tasks.
"""
import logging
import asyncio
import uuid
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SwarmTool:
    """
    Spawns one or more child Archimedes agent instances to work on
    sub-tasks in parallel. Each child gets its own isolated context.
    Results are aggregated and returned to the parent.
    """

    def __init__(self):
        self._parent_agent = None  # Injected after registration

    def bind_parent(self, executor_agent):
        """Called during tool registration to link the parent agent."""
        self._parent_agent = executor_agent

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "spawn_agents",
                "description": (
                    "SWARM MODE: Spawn one or more parallel child agents for complex tasks. "
                    "Each agent works independently with its own context, sandbox, and tools. "
                    "Use this for fullstack features: e.g. one agent does frontend, "
                    "another does backend, a third writes tests. "
                    "All agents run in parallel and their outputs are merged. "
                    "Each agent entry needs a 'role' (e.g. 'frontend', 'backend', 'tester') "
                    "and a 'task' description."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agents": {
                            "type": "array",
                            "description": "List of agent specs to spawn in parallel.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {
                                        "type": "string",
                                        "description": "Agent role: frontend, backend, tester, researcher, devops, etc."
                                    },
                                    "task": {
                                        "type": "string",
                                        "description": "Specific sub-task for this agent to complete."
                                    }
                                },
                                "required": ["role", "task"]
                            }
                        }
                    },
                    "required": ["agents"]
                }
            }
        }

    async def execute(self, session_id: str, agents: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self._parent_agent:
            return {"success": False, "error": "SwarmTool not bound to parent agent."}

        if not agents or len(agents) == 0:
            return {"success": False, "error": "No agent specs provided."}

        if len(agents) > 5:
            return {"success": False, "error": "Max 5 parallel agents allowed."}

        logger.info(f"🐝 Swarm spawning {len(agents)} child agents: {[a['role'] for a in agents]}")

        from backend.agent.orchestration.state import OrchestrationState, AgentMode

        async def run_child(agent_spec: Dict[str, str]) -> Dict[str, Any]:
            role = agent_spec["role"]
            task = agent_spec["task"]
            child_session = f"{session_id}_swarm_{role}_{uuid.uuid4().hex[:6]}"

            child_state = OrchestrationState(
                session_id=child_session,
                task_description=f"[SWARM/{role.upper()}] {task}",
                mode=AgentMode.FAST
            )
            child_state.task_hint = "execute"

            try:
                result_state = await self._parent_agent.process(child_state)

                outputs = []
                for r in result_state.results:
                    out = r.get("output", "")
                    if out:
                        outputs.append(out)

                final_output = "\n".join(outputs[-3:]) if outputs else "Completed (no output)."

                # Broadcast to EventBus
                if hasattr(self._parent_agent, "event_bus") and self._parent_agent.event_bus:
                    await self._parent_agent.event_bus.emit_thought(
                        f"🐝 Swarm child [{role}] completed: {final_output[:80]}",
                        agent=f"swarm_{role}"
                    )

                return {
                    "role": role,
                    "success": True,
                    "output": final_output[:3000],
                    "confidence": getattr(result_state, "confidence_score", 100)
                }
            except Exception as e:
                logger.error(f"Swarm child [{role}] failed: {e}")
                return {"role": role, "success": False, "error": str(e)}

        # Run all children in parallel
        results = await asyncio.gather(*[run_child(spec) for spec in agents])

        all_succeeded = all(r["success"] for r in results)
        merged_output = "\n\n".join(
            f"═══ [{r['role'].upper()}] ═══\n{r.get('output', r.get('error', 'N/A'))}"
            for r in results
        )

        return {
            "success": all_succeeded,
            "output": merged_output[:8000],
            "agent_count": len(results),
            "results": results
        }
