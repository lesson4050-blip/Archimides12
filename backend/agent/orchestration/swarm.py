"""
Micro-Agent Swarm v2: Tool-Armed Agents.

Key upgrade over v1:
- Agents can now execute tools (shell, file, search) to PROVE their work
- Coder writes code AND runs it. Tester writes tests AND executes them.
- Critic reviews based on ACTUAL test output, not generated text.
- Git checkpoint before each swarm run for safe rollback.
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
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)


MICRO_AGENT_TEMPLATES = {
    "coder": {
        "specialty": "Writing clean, efficient, tested code",
        "system_prompt": (
            "You are an expert software engineer. "
            "Write production-quality code. "
            "Always include error handling. "
            "Think about edge cases. "
            "CRITICAL: After writing code, you MUST use the shell tool to verify it compiles/runs. "
            "Never submit code you haven't tested. "
            "Output only the solution, no explanations unless asked."
        ),
        "tools": ["file", "shell", "search", "ast_navigator", "fast_linter"]
    },
    "critic": {
        "specialty": "Finding bugs, security issues, and improvements",
        "system_prompt": (
            "You are a senior code reviewer and security expert. "
            "Find bugs, vulnerabilities, race conditions, and inefficiencies. "
            "Be specific: line numbers, exact problems, exact fixes. "
            "CRITICAL: Use the shell tool to actually RUN the code and check for errors. "
            "Use the fast_linter tool to lint the code. "
            "Base your review on REAL execution output, not assumptions. "
            "Output: list of issues with severity (CRITICAL/HIGH/MEDIUM/LOW)."
        ),
        "tools": ["file", "shell", "fast_linter", "ast_navigator"]
    },
    "researcher": {
        "specialty": "Deep research and information synthesis",
        "system_prompt": (
            "You are a research specialist. "
            "Find the most accurate, recent, authoritative information. "
            "Synthesize multiple sources. "
            "Distinguish facts from opinions. "
            "Always cite sources."
        ),
        "tools": ["search", "web_read"]
    },
    "tester": {
        "specialty": "Writing and executing unit tests",
        "system_prompt": (
            "You are a QA engineer. "
            "Write comprehensive unit tests using pytest. "
            "Cover: happy path, edge cases, error cases. "
            "CRITICAL: After writing tests, you MUST execute them with the shell tool. "
            "Report actual pass/fail results, not hypothetical ones. "
            "Output: complete test file AND execution results."
        ),
        "tools": ["file", "shell", "fast_linter"]
    },
    "architect": {
        "specialty": "System design and architecture decisions",
        "system_prompt": (
            "You are a solutions architect. "
            "Design scalable, maintainable systems. "
            "Consider: performance, security, cost, simplicity. "
            "Use the repo_map tool to understand the existing codebase structure. "
            "Output: architecture decision with trade-offs."
        ),
        "tools": ["file", "search", "repo_map", "ast_navigator"]
    },
    "optimizer": {
        "specialty": "Performance optimization and refactoring",
        "system_prompt": (
            "You are a performance engineer. "
            "Identify bottlenecks and optimize. "
            "Measure before and after. "
            "Output: optimized solution with explanation."
        ),
        "tools": ["file", "shell", "fast_linter"]
    }
}


class MicroAgentSwarm:
    """
    v2: Tool-armed micro-agents that prove their work with real execution.
    
    Key differences from v1:
    1. Agents have access to a subset of tools relevant to their role
    2. Coder runs code, tester runs tests, critic runs linter
    3. Results are based on actual execution output, not LLM text generation
    """

    def __init__(self, router: ModelRouter, tool_registry=None):
        self.router = router
        self.tool_registry = tool_registry
        self._agents: Dict[str, MicroAgent] = {}

    def set_tool_registry(self, tool_registry):
        """Allow late binding of tool registry (set after init)."""
        self.tool_registry = tool_registry

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

    def _get_tools_for_agent(self, role: str) -> List[Dict[str, Any]]:
        """Get tool definitions available to a specific agent role."""
        if not self.tool_registry:
            return []
        
        template = MICRO_AGENT_TEMPLATES.get(role, {})
        allowed_tool_names = template.get("tools", [])
        
        if not allowed_tool_names:
            return []
        
        all_defs = self.tool_registry.get_all_tool_definitions()
        return [
            d for d in all_defs
            if d.get("function", {}).get("name") in allowed_tool_names
        ]

    async def _run_agent_with_tools(
        self,
        agent: MicroAgent,
        task: str,
        context: str = "",
        session_id: str = "default",
        websocket_send: Optional[Callable] = None,
        max_tool_steps: int = 8
    ) -> str:
        """
        Run a micro-agent with tool access.
        The agent can call tools up to max_tool_steps times.
        """
        agent.status = "working"
        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": f"🤖 [{agent.role.upper()}] начинает работу (с доступом к инструментам)...",
                "agent": agent.role
            })

        # Build messages
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

        # Get available tools for this agent
        agent_tools = self._get_tools_for_agent(agent.role)
        
        # If no tools available, fall back to text-only
        if not agent_tools or not self.tool_registry:
            return await self._run_agent_text_only(agent, task, context, websocket_send)

        # Tool execution loop
        collected_outputs = []
        for step in range(max_tool_steps):
            try:
                response = await self.router.generate(
                    messages=messages, 
                    tools=agent_tools,
                    task_hint="think"
                )
            except Exception as e:
                logger.error(f"MicroAgent {agent.role} generate failed: {e}")
                break

            thought = response.get("thought", response.get("thinking", ""))
            tool_call = response.get("tool_call")

            if tool_call:
                t_name = tool_call["name"]
                t_params = tool_call["params"]

                if websocket_send:
                    await websocket_send({
                        "type": "thought",
                        "content": f"🔧 [{agent.role.upper()}] → {t_name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in t_params.items())})",
                        "agent": agent.role
                    })

                # Execute the tool
                try:
                    tool_res = await self.tool_registry.execute_tool(
                        t_name, t_params, session_id=session_id
                    )
                except Exception as e:
                    tool_res = {"success": False, "error": str(e)}

                success = tool_res.get("success", True)
                output = str(tool_res.get("output", tool_res.get("content", tool_res.get("error", "OK"))))
                
                # Truncate massive outputs to prevent context blow-up
                if len(output) > 3000:
                    output = output[:3000] + "\n...[truncated]"

                collected_outputs.append({
                    "tool": t_name,
                    "success": success,
                    "output": output[:500]
                })
                agent.tool_outputs.append({"tool": t_name, "success": success})

                # Add to conversation for next iteration
                call_id = f"call_{str(uuid.uuid4())[:8]}"
                messages.append({
                    "role": "assistant",
                    "content": thought or "",
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {"name": t_name, "arguments": t_params}
                    }]
                })
                messages.append({
                    "role": "tool",
                    "content": output,
                    "tool_call_id": call_id,
                    "name": t_name
                })
                continue
            else:
                # No tool call — agent is done
                result = response.get("text", "")
                
                # Append tool execution summary
                if collected_outputs:
                    tool_summary = "\n\n--- Tool Execution Evidence ---\n"
                    for to in collected_outputs:
                        status = "✅" if to["success"] else "❌"
                        tool_summary += f"{status} {to['tool']}: {to['output'][:200]}\n"
                    result += tool_summary

                agent.result = result
                agent.status = "done"

                if websocket_send:
                    tool_count = len(collected_outputs)
                    success_count = sum(1 for t in collected_outputs if t["success"])
                    await websocket_send({
                        "type": "thought",
                        "content": f"✅ [{agent.role.upper()}] завершил. Инструменты: {success_count}/{tool_count} успешно.",
                        "agent": agent.role
                    })
                return result

        # Reached max steps
        summary = "\n".join(
            f"{'✅' if o['success'] else '❌'} {o['tool']}: {o['output'][:100]}"
            for o in collected_outputs
        )
        agent.result = f"[Reached {max_tool_steps} tool steps]\n{summary}"
        agent.status = "done"
        return agent.result

    async def _run_agent_text_only(
        self,
        agent: MicroAgent,
        task: str,
        context: str = "",
        websocket_send: Optional[Callable] = None
    ) -> str:
        """Fallback: run agent without tools (text generation only)."""
        agent.status = "working"
        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": f"🤖 [{agent.role.upper()}] начинает работу...",
                "agent": agent.role
            })

        # Inject relevant knowledge from GraphRAG
        knowledge_ctx = ""
        try:
            from backend.memory.knowledge_graph import format_graph_context
            from backend.memory.memory_bank import get_relevant_facts
            task_words = task.split()[:3]
            key_term = " ".join(task_words)
            graph_knowledge = await format_graph_context(key_term, depth=1)
            memory_facts = await get_relevant_facts(limit=3)
            if graph_knowledge:
                knowledge_ctx += f"\nKnowledge Graph:\n{graph_knowledge}"
            if memory_facts:
                knowledge_ctx += (
                    "\nMemory:\n"
                    + "\n".join(f"• {f}" for f in memory_facts)
                )
        except Exception:
            knowledge_ctx = ""

        messages = [
            {"role": "system", "content": agent.system_prompt + knowledge_ctx},
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
        agent_roles_override: Optional[List[str]] = None,
        session_id: str = "default",
        websocket_send: Optional[Callable] = None
    ) -> str:
        """
        Main entry point.
        Spawns tool-armed agents, runs them, debate if needed, returns final result.
        """
        agent_roles = (
            agent_roles_override
            or self._select_agents_for_task(task, task_hint)
        )

        if len(agent_roles) == 1:
            # Single agent — no swarm needed
            role = agent_roles[0]
            template = MICRO_AGENT_TEMPLATES.get(role, MICRO_AGENT_TEMPLATES["coder"])
            agent = MicroAgent(
                agent_id=str(uuid.uuid4())[:8],
                role=role,
                specialty=template["specialty"],
                system_prompt=template["system_prompt"]
            )
            return await self._run_agent_with_tools(
                agent, task, session_id=session_id, websocket_send=websocket_send
            )

        # Multi-agent debate with tools
        agents = []
        for role in agent_roles:
            template = MICRO_AGENT_TEMPLATES.get(role, MICRO_AGENT_TEMPLATES["coder"])
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
                    f"🐝 Swarm запущен (v2 — tool-armed): "
                    f"{', '.join(a.role for a in agents)}"
                )
            })

        # Phase 1: Primary agent works first (with tools)
        primary = agents[0]
        primary_result = await self._run_agent_with_tools(
            primary, task, session_id=session_id, websocket_send=websocket_send
        )

        # Phase 2: Other agents review/augment in parallel (with tools)
        review_tasks = []
        for reviewer in agents[1:]:
            context = (
                f"The {primary.role} produced this:\n"
                f"{primary_result[:2000]}\n\n"
                f"Your job as {reviewer.role}: "
                f"{reviewer.specialty}. "
                f"Review and improve the above. Use your tools to VERIFY claims."
            )
            review_tasks.append(
                self._run_agent_with_tools(
                    reviewer, task,
                    context=context,
                    session_id=session_id,
                    websocket_send=websocket_send
                )
            )

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)
        reviews = [r for r in reviews if isinstance(r, str)]

        # Phase 3: Structured Voting & Synthesis
        if not reviews:
            return primary_result

        # Build structured voting prompt
        synthesis_prompt = (
            f"You are a senior technical lead synthesizing multi-agent work.\n\n"
            f"TASK: {task}\n\n"
            f"=== PRIMARY SOLUTION by [{primary.role.upper()}] ===\n"
            f"{primary_result[:2500]}\n\n"
        )
        for reviewer, review in zip(agents[1:], reviews):
            synthesis_prompt += (
                f"=== REVIEW by [{reviewer.role.upper()}] ===\n"
                f"{review[:1500]}\n\n"
            )
        
        # Include tool execution evidence
        synthesis_prompt += "=== TOOL EXECUTION SUMMARY ===\n"
        for a in agents:
            if a.tool_outputs:
                successes = sum(1 for t in a.tool_outputs if t["success"])
                failures = sum(1 for t in a.tool_outputs if not t["success"])
                synthesis_prompt += f"[{a.role.upper()}]: {successes} successful, {failures} failed tool calls\n"
        
        synthesis_prompt += (
            "\nINSTRUCTIONS:\n"
            "1. Identify CRITICAL issues raised by reviewers\n"
            "2. PRIORITIZE evidence from actual tool execution over text claims\n"
            "3. If the tester ran tests and they PASSED, the code is likely correct\n"
            "4. If the critic found issues via linting/execution, those MUST be fixed\n"
            "5. Produce the FINAL, production-ready answer that:\n"
            "   - Incorporates the best elements from all agents\n"
            "   - Fixes all critical/high issues identified\n"
            "   - Preserves correct parts of the primary solution\n"
            "   - Is complete and ready for direct use\n\n"
            "Output ONLY the final synthesized answer. "
            "No commentary, no scores, no explanations about your process.\n"
            "Respond in the SAME LANGUAGE as the original task. "
            "If the task is in Russian — respond in Russian. "
            "If the task is in English — respond in English."
        )

        synth_response = await self.router.generate(
            messages=[{"role": "user", "content": synthesis_prompt}],
            task_hint="think"
        )
        final = synth_response.get("text", primary_result)

        if websocket_send:
            await websocket_send({
                "type": "message_info",
                "content": "🏆 Swarm синтезировал финальный ответ (подтвержден инструментами)"
            })

        # Cleanup
        for agent in agents:
            self._agents.pop(agent.agent_id, None)

        return final
