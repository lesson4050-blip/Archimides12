"""
Micro-Agent Swarm: динамически создаёт специализированных агентов
под каждую подзадачу и уничтожает их после завершения.
Агенты дискутируют через общее состояние до достижения консенсуса.
"""
import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)


@dataclass
class MicroAgent:
    agent_id: str
    role: str
    specialty: str
    system_prompt: str
    result: Optional[str] = None
    status: str = "idle"  # idle, working, done, error


MICRO_AGENT_TEMPLATES = {
    "coder": {
        "specialty": "Writing clean, efficient, tested code",
        "system_prompt": (
            "You are an expert software engineer. "
            "Write production-quality code. "
            "Always include error handling. "
            "Think about edge cases. "
            "Output only the solution, no explanations unless asked."
        )
    },
    "critic": {
        "specialty": "Finding bugs, security issues, and improvements",
        "system_prompt": (
            "You are a senior code reviewer and security expert. "
            "Find bugs, vulnerabilities, race conditions, and inefficiencies. "
            "Be specific: line numbers, exact problems, exact fixes. "
            "Output: list of issues with severity (CRITICAL/HIGH/MEDIUM/LOW)."
        )
    },
    "researcher": {
        "specialty": "Deep research and information synthesis",
        "system_prompt": (
            "You are a research specialist. "
            "Find the most accurate, recent, authoritative information. "
            "Synthesize multiple sources. "
            "Distinguish facts from opinions. "
            "Always cite sources."
        )
    },
    "tester": {
        "specialty": "Writing and executing unit tests",
        "system_prompt": (
            "You are a QA engineer. "
            "Write comprehensive unit tests using pytest. "
            "Cover: happy path, edge cases, error cases. "
            "Output: complete test file ready to run."
        )
    },
    "architect": {
        "specialty": "System design and architecture decisions",
        "system_prompt": (
            "You are a solutions architect. "
            "Design scalable, maintainable systems. "
            "Consider: performance, security, cost, simplicity. "
            "Output: architecture decision with trade-offs."
        )
    },
    "optimizer": {
        "specialty": "Performance optimization and refactoring",
        "system_prompt": (
            "You are a performance engineer. "
            "Identify bottlenecks and optimize. "
            "Measure before and after. "
            "Output: optimized solution with explanation."
        )
    }
}


class MicroAgentSwarm:
    """
    Instantiates micro-agents dynamically, runs them in parallel or sequence,
    lets them debate/review each other's output, then synthesizes final answer.
    """

    def __init__(self, router: ModelRouter):
        self.router = router
        self._agents: Dict[str, MicroAgent] = {}

    def _select_agents_for_task(self, task: str, task_hint: str) -> List[str]:
        """Select which micro-agents to spawn based on task type."""
        task_lower = task.lower()

        if task_hint == "execute" or any(
            kw in task_lower for kw in
            ["code", "script", "function", "implement", "write", "код", "напиши"]
        ):
            return ["coder", "critic", "tester"]

        if task_hint == "search" or any(
            kw in task_lower for kw in
            ["research", "find", "compare", "analyze", "исследуй", "найди"]
        ):
            return ["researcher", "critic"]

        if any(kw in task_lower for kw in
               ["design", "architecture", "system", "архитектура", "дизайн"]):
            return ["architect", "coder", "critic"]

        # Default: single executor
        return ["coder"]

    async def _run_agent(
        self,
        agent: MicroAgent,
        task: str,
        context: str = "",
        websocket_send: Optional[Callable] = None
    ) -> str:
        """Run a single micro-agent on a task."""
        agent.status = "working"
        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": f"🤖 [{agent.role.upper()}] начинает работу...",
                "agent": agent.role
            })

        messages = [
            {"role": "system", "content": agent.system_prompt},
        ]
        if context:
            messages.append({
                "role": "user",
                "content": f"Context from previous agents:\n{context}\n\nTask: {task}"
            })
        else:
            messages.append({"role": "user", "content": task})

        try:
            response = await self.router.generate(
                messages=messages, task_hint="think"
            )
            result = response.get("text", "")
            agent.result = result
            agent.status = "done"

            if websocket_send:
                await websocket_send({
                    "type": "thought",
                    "content": f"✅ [{agent.role.upper()}] завершил.",
                    "agent": agent.role
                })
            return result
        except Exception as e:
            agent.status = "error"
            logger.error(f"MicroAgent {agent.role} failed: {e}")
            return f"[{agent.role} failed: {e}]"

    async def run(
        self,
        task: str,
        task_hint: str = "default",
        websocket_send: Optional[Callable] = None
    ) -> str:
        """
        Main entry point.
        Spawns agents, runs them, debate if needed, returns final result.
        """
        agent_roles = self._select_agents_for_task(task, task_hint)

        if len(agent_roles) == 1:
            # Single agent — no swarm needed
            role = agent_roles[0]
            template = MICRO_AGENT_TEMPLATES[role]
            agent = MicroAgent(
                agent_id=str(uuid.uuid4())[:8],
                role=role,
                specialty=template["specialty"],
                system_prompt=template["system_prompt"]
            )
            return await self._run_agent(agent, task,
                                         websocket_send=websocket_send)

        # Multi-agent debate
        agents = []
        for role in agent_roles:
            template = MICRO_AGENT_TEMPLATES[role]
            agent = MicroAgent(
                agent_id=str(uuid.uuid4())[:8],
                role=role,
                specialty=template["specialty"],
                system_prompt=template["system_prompt"]
            )
            agents.append(agent)
            self._agents[agent.agent_id] = agent

        if websocket_send:
            await websocket_send({
                "type": "message_info",
                "content": (
                    f"🐝 Swarm запущен: "
                    f"{', '.join(a.role for a in agents)}"
                )
            })

        # Phase 1: Primary agent works first
        primary = agents[0]
        primary_result = await self._run_agent(
            primary, task, websocket_send=websocket_send
        )

        # Phase 2: Other agents review/augment in parallel
        review_tasks = []
        for reviewer in agents[1:]:
            context = (
                f"The {primary.role} produced this:\n"
                f"{primary_result[:2000]}\n\n"
                f"Your job as {reviewer.role}: "
                f"{reviewer.specialty}. "
                f"Review and improve the above."
            )
            review_tasks.append(
                self._run_agent(
                    reviewer, task,
                    context=context,
                    websocket_send=websocket_send
                )
            )

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)
        reviews = [r for r in reviews if isinstance(r, str)]

        # Phase 3: Synthesize
        if not reviews:
            return primary_result

        synthesis_prompt = (
            f"Original task: {task}\n\n"
            f"Primary solution by {primary.role}:\n{primary_result}\n\n"
        )
        for i, (reviewer, review) in enumerate(
            zip(agents[1:], reviews), 1
        ):
            synthesis_prompt += (
                f"Review/improvements by {reviewer.role}:\n{review}\n\n"
            )
        synthesis_prompt += (
            "Synthesize the best final answer incorporating all insights. "
            "Output only the final result."
        )

        synth_response = await self.router.generate(
            messages=[{"role": "user", "content": synthesis_prompt}],
            task_hint="think"
        )
        final = synth_response.get("text", primary_result)

        if websocket_send:
            await websocket_send({
                "type": "message_info",
                "content": "🏆 Swarm синтезировал финальный ответ"
            })

        # Cleanup
        for agent in agents:
            self._agents.pop(agent.agent_id, None)

        return final
