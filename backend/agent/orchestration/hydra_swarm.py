"""
Hydra Swarm — hierarchical multi-agent swarm.
Commander → [Scout ‖ Warrior] → Sentinel → Commander synthesis.
Each agent has isolated history. Communication via structured messages.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    from_role: str
    content: str
    confidence: float = 1.0
    artifacts: List[str] = field(default_factory=list)

    def to_context(self) -> str:
        return f"[{self.from_role.upper()} | conf={self.confidence:.2f}]\n{self.content}"


class HydraAgent:
    """Single agent with isolated history."""

    def __init__(self, role: str, system_prompt: str, router, tool_registry=None):
        self.role = role
        self.router = router
        self.tool_registry = tool_registry
        self.history: List[Dict] = [
            {"role": "system", "content": system_prompt}
        ]
        ROLE_HINTS = {
            "scout": "fast",
            "warrior": "code",
            "sentinel": "think",
            "commander": "plan",
        }
        self.task_hint = ROLE_HINTS.get(self.role, "default")

    def _get_tools_for_role(self) -> list:
        """Get tool definitions appropriate for this agent's role."""
        from backend.agent.tool_selector import select_tools
        
        # Get all tool definitions from registry
        if not hasattr(self, 'tool_registry') or not self.tool_registry:
            return []
        
        all_tools = []
        for tool_name, tool_fn in self.tool_registry.tools.items():
            # Build OpenAI-compatible tool definition
            import inspect
            try:
                sig = inspect.signature(tool_fn)
                params = {}
                required = []
                for pname, param in sig.parameters.items():
                    if pname in ('self', 'kwargs', 'args'):
                        continue
                    params[pname] = {"type": "string", "description": pname}
                    if param.default == inspect.Parameter.empty:
                        required.append(pname)
                
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Tool: {tool_name}",
                        "parameters": {
                            "type": "object",
                            "properties": params,
                            "required": required
                        }
                    }
                })
            except Exception:
                pass
        
        # Select relevant tools for this role
        task = self.history[-1].get("content", "") if self.history else ""
        return select_tools(task, all_tools, max_tools=6)

    async def run(
        self,
        task: str,
        context_messages: List[AgentMessage] = None,
        max_iters: int = 8,
        done_signal: str = None
    ) -> AgentMessage:
        context_parts = [f"Task: {task}"]
        if context_messages:
            context_parts.append("Context from other agents:")
            for m in context_messages:
                context_parts.append(m.to_context())

        self.history.append({
            "role": "user",
            "content": "\n\n".join(context_parts)
        })

        done_signal = done_signal or f"{self.role.upper()}_DONE"
        last_text = ""

        for _ in range(max_iters):
            tools = self._get_tools_for_role()
            response = await self.router.generate(
                messages=self.history,
                tools=tools if tools else None,
                task_hint=self.task_hint
            )
            text = response.get("text", "")
            if not text:
                break
            self.history.append({"role": "assistant", "content": text})
            last_text = text

            if done_signal in text:
                break

            # Execute tool calls if any
            tool_calls = response.get("tool_calls", [])
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_params = tc.get("params", {})
                if tool_name and hasattr(self, 'tool_registry') and self.tool_registry:
                    try:
                        tool_result = await self.tool_registry.execute_tool(
                            tool_name, tool_params
                        )
                        # Add tool result to history
                        self.history.append({
                            "role": "tool",
                            "content": str(tool_result.get("output", tool_result))[:2000],
                            "tool_name": tool_name
                        })
                    except Exception as e:
                        logger.warning(f"[Hydra] Tool {tool_name} failed: {e}")

            self.history.append({
                "role": "user",
                "content": "Continue. Execute your next step."
            })

        return AgentMessage(
            from_role=self.role,
            content=last_text or f"{self.role} completed without output.",
            confidence=0.8
        )


SCOUT_PROMPT = """You are SCOUT — the research specialist.
Your job: explore the codebase, understand the problem, find relevant files.
Tools: repo_map, file(read), search, ast_navigator
NEVER write or modify code. Only read and report.
Be precise: cite file:line references for every finding.
When done, write SCOUT_DONE followed by a structured findings summary."""

WARRIOR_PROMPT = """You are WARRIOR — the implementation specialist.
Your job: write the minimal correct fix based on Scout's findings.
Tools: code_edit, file, shell, patch, git
Rules:
- Read every file BEFORE editing it
- Use code_edit(find_replace) for surgical changes, not full rewrites
- Run the specific failing test after each change
- Minimal patch only — no unrelated refactoring
When done, write WARRIOR_DONE followed by what you changed."""

SENTINEL_PROMPT = """You are SENTINEL — the quality guardian.
Your job: verify that Warrior's fix actually works.
Mandatory steps:
1. Run ALL tests: shell("pytest -x --tb=short")
2. Lint changed files: shell("ruff check <files>")  
3. Re-read original task: does the fix cover ALL requirements?
Output a structured verdict:
SENTINEL_VERDICT: PASS or FAIL
Tests: X passed, Y failed
Issues: (list any problems)
Score: 0.0-1.0"""


class HydraCommander:
    def __init__(self, router):
        self.router = router

    async def plan_attack(self, task: str) -> List[Dict[str, str]]:
        """Break task into subtasks for Scout and Warrior."""
        response = await self.router.generate(
            messages=[
                {"role": "system", "content": (
                    "You are a task planner. Break the given task into "
                    "3-5 concrete subtasks. Output as JSON list: "
                    '[{"role": "scout"|"warrior", "task": "..."}]'
                )},
                {"role": "user", "content": f"Task: {task}"}
            ],
            task_hint="plan"
        )
        text = response.get("text", "[]")
        try:
            import json, re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            return json.loads(match.group()) if match else []
        except Exception:
            return [{"role": "scout", "task": task},
                    {"role": "warrior", "task": task}]

    def synthesize(
        self,
        task: str,
        scout_msg: AgentMessage,
        warrior_msg: AgentMessage,
        sentinel_msg: AgentMessage
    ) -> str:
        verdict = sentinel_msg.content
        passed = "PASS" in verdict
        return (
            f"=== Hydra Swarm Results ===\n\n"
            f"Task: {task}\n\n"
            f"Scout findings:\n{scout_msg.content[:600]}\n\n"
            f"Warrior changes:\n{warrior_msg.content[:600]}\n\n"
            f"Sentinel verdict:\n{verdict[:600]}\n\n"
            f"Outcome: {'✅ SUCCESS' if passed else '❌ NEEDS REVIEW'}"
        )


class HydraScout(HydraAgent):
    def __init__(self, router, tool_registry=None):
        super().__init__("scout", SCOUT_PROMPT, router, tool_registry=tool_registry)

    async def investigate(self, task: str) -> AgentMessage:
        return await self.run(task, done_signal="SCOUT_DONE", max_iters=8)


class HydraWarrior(HydraAgent):
    def __init__(self, router, tool_registry=None):
        super().__init__("warrior", WARRIOR_PROMPT, router, tool_registry=tool_registry)

    async def execute(
        self, task: str, context: List[AgentMessage]
    ) -> AgentMessage:
        return await self.run(
            task, context_messages=context,
            done_signal="WARRIOR_DONE", max_iters=12
        )


class HydraSentinel(HydraAgent):
    def __init__(self, router, tool_registry=None):
        super().__init__("sentinel", SENTINEL_PROMPT, router, tool_registry=tool_registry)

    async def verify(
        self, task: str, context: List[AgentMessage]
    ) -> AgentMessage:
        return await self.run(
            task, context_messages=context,
            done_signal="SENTINEL_VERDICT", max_iters=6
        )


class HydraSwarm:
    """Orchestrates Scout → Warrior → Sentinel pipeline."""

    def __init__(self, router, tool_registry=None):
        self.router = router
        self.tool_registry = tool_registry
        self.commander = HydraCommander(router)
        self.scout = HydraScout(router, tool_registry=tool_registry)
        self.warrior = HydraWarrior(router, tool_registry=tool_registry)
        self.sentinel = HydraSentinel(router, tool_registry=tool_registry)

    async def run(
        self,
        task: str,
        websocket_send=None
    ) -> Dict[str, Any]:
        start = time.time()

        def _emit(msg: str):
            if websocket_send:
                asyncio.ensure_future(websocket_send({
                    "type": "thought", "content": msg
                }))

        _emit("🐉 Hydra Swarm activating...")

        # Phase 1: Scout
        _emit("🔍 Scout: exploring codebase...")
        scout_result = await self.scout.investigate(task)

        # Phase 2: Warrior (with Scout context)
        _emit("⚔️ Warrior: implementing fix...")
        warrior_result = await self.warrior.execute(
            task, context=[scout_result]
        )

        # Phase 3: Sentinel (with both contexts)
        _emit("🛡️ Sentinel: verifying...")
        sentinel_result = await self.sentinel.verify(
            task, context=[scout_result, warrior_result]
        )

        # Synthesis
        synthesis = self.commander.synthesize(
            task, scout_result, warrior_result, sentinel_result
        )

        passed = "PASS" in sentinel_result.content
        return {
            "success": passed,
            "output": synthesis,
            "duration": round(time.time() - start, 2),
            "agents_used": ["scout", "warrior", "sentinel"],
            "verdict": sentinel_result.content
        }
