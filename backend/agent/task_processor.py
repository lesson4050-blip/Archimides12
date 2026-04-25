"""
Task Processor — Legacy fallback execution path.

# LEGACY EXECUTION PATH
# These methods are used as fallback if AgentOrchestrator.run_task() raises.
# Primary execution: core.py -> orchestrator.run_task()
# Fallback execution: core.py -> task_processor.execute_with_fallback()
"""
import asyncio
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Callable

from backend.config import settings

logger = logging.getLogger(__name__)


class TaskProcessor:
    """
    Legacy task execution engine.
    Contains plan creation, execution, subtask handling, and error recovery.
    Only used if the primary AgentOrchestrator path fails.
    """

    def __init__(self, router, context_manager, tool_registry, session_id: str,
                 tool_def_cache=None, history: list = None, system_prompt: str = ""):
        self.router = router
        self.context_manager = context_manager
        self.tool_registry = tool_registry
        self.session_id = session_id
        self.tool_def_cache = tool_def_cache
        self.history = history or []
        self.system_prompt = system_prompt

    @property
    def tools(self):
        return self.tool_registry.tools

    # ── FIX 3: LLM-based complexity analysis (replaces Russian keyword heuristic) ──

    async def _analyze_complexity(self, task_description: str) -> float:
        """Analyze task complexity via LLM classification (0.0–1.0)."""
        prompt = (
            "Rate the complexity of this task on a scale from 0.0 to 1.0.\n"
            "0.0 = trivial (rename a variable), 1.0 = very complex "
            "(design and implement a distributed system).\n"
            f"Task: {task_description}\n"
            "Reply with ONLY a float number between 0.0 and 1.0. Nothing else."
        )
        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="quick"
            )
            return min(1.0, max(0.0, float(response.get("text", "0.5").strip())))
        except (ValueError, TypeError):
            return 0.5

    # ── LEGACY: Plan creation ──

    async def _create_plan(self, task_id: str, description: str,
                           websocket_send: Callable = None, **kwargs):
        """Create an intelligent execution plan. LEGACY fallback only."""
        from backend.agent.core import TaskPlan

        if websocket_send:
            await websocket_send({"type": "thought", "content": f"Planning: '{description}'"})

        if not self.history or self.history[0].get("role") != "system":
            self.history = [{"role": "system", "content": self.system_prompt}]
        self.history.append({"role": "user", "content": description})
        self.context_manager.add_message("user", description)

        try:
            await self.context_manager.summarize_if_needed(self.router)
            self.history = self.context_manager.get_messages()
        except Exception as e:
            logger.warning(f"Context summarization skipped: {e}")

        complexity = await self._analyze_complexity(description)
        strategy = "adaptive" if complexity > 0.7 else "sequential"
        subtasks = await self._decompose_task(description, complexity)

        return TaskPlan(
            task_id=task_id,
            description=description,
            subtasks=subtasks,
            strategy=strategy,
            priority=kwargs.get("priority", 1),
            estimated_duration=complexity * 10
        )

    # ── LEGACY: Plan execution ──

    async def _execute_plan(self, task_id: str, plan, websocket_send: Callable = None):
        """Execute a plan with optimal strategy. LEGACY fallback only."""
        results = []
        if plan.strategy == "parallel":
            tasks = [
                self._execute_subtask(task_id, st, websocket_send=websocket_send)
                for st in plan.subtasks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for subtask in plan.subtasks:
                result = await self._execute_subtask(task_id, subtask, websocket_send=websocket_send)
                results.append(result)
        return self._synthesize_results(results)

    # ── LEGACY: Subtask execution with FIX 6 (verification loop) ──

    async def _execute_subtask(self, task_id: str, subtask: Dict[str, Any],
                               websocket_send: Callable = None):
        """Execute a subtask using LLM + tools. LEGACY fallback only."""
        try:
            subtask_type = subtask.get("type", "generic")
            action_map = {
                "analyze": "Analyzing task...",
                "execute": "Executing main step...",
                "verify": "Verifying results...",
                "optimize": "Optimizing solution...",
                "plan": "Refining plan..."
            }
            msg = action_map.get(subtask_type, f"Executing step: {subtask_type}")
            if websocket_send:
                await websocket_send({"type": "message_info", "content": msg})

            if subtask_type in ["execute", "analyze", "verify", "optimize"]:
                max_steps = settings.AGENT_MAX_ITERATIONS
                subtask_results = []
                tool_defs = self.tool_def_cache.get_definitions() if self.tool_def_cache else []

                for step in range(max_steps):
                    async def handle_token(token_event):
                        if websocket_send:
                            await websocket_send(token_event)

                    if hasattr(self.router, "generate_stream"):
                        response = await self.router.generate_stream(
                            messages=self.history, tools=tool_defs,
                            task_hint="think" if step == 0 else "default",
                            on_token=handle_token
                        )
                    else:
                        response = await self.router.generate(
                            messages=self.history, tools=tool_defs,
                            task_hint="think" if step == 0 else "default"
                        )

                    thought = response.get("thought", "")
                    if thought and websocket_send:
                        await websocket_send({"type": "thought", "content": thought})

                    tool_call = response.get("tool_call")
                    if tool_call:
                        t_name = tool_call["name"]
                        t_params = tool_call["params"]

                        if websocket_send:
                            friendly = {
                                "search": f"Searching: {t_params.get('query', '')}...",
                                "file": f"Working with file {t_params.get('path', '')}...",
                                "shell": f"Running command: {t_params.get('command', '')}...",
                                "browser": "Browsing web page..."
                            }
                            await websocket_send({
                                "type": "message_info",
                                "content": friendly.get(t_name, f"Using tool: {t_name}")
                            })

                        if t_name in self.tools:
                            call_id = f"call_{str(uuid.uuid4())[:8]}"
                            std_tool_call = {
                                "id": call_id, "type": "function",
                                "function": {"name": t_name, "arguments": t_params}
                            }

                            TOOLS_NEEDING_SESSION = [
                                "file", "shell", "browser", "voice",
                                "document", "slides", "expose", "plan", "monitor"
                            ]
                            t_args = {**t_params}
                            if t_name in TOOLS_NEEDING_SESSION:
                                t_args["session_id"] = self.session_id

                            res = await self.tools[t_name](**t_args)

                            if res.get("success") is False:
                                tool_output = f"ERROR: {res.get('error', 'Unknown error')}"
                            else:
                                tool_output = str(res.get("output", res.get("content", "OK")))

                            logger.info(f"TOOL DONE: {t_name}. Len: {len(tool_output)}")

                            self.context_manager.add_message("assistant", thought or "", tool_calls=[std_tool_call])
                            self.context_manager.add_message("tool", tool_output, tool_call_id=call_id, name=t_name)
                            await self.context_manager.summarize_if_needed(self.router)
                            self.history = self.context_manager.get_messages()

                            # Artifact support
                            if t_name == "file" and t_params.get("action") == "write" and res.get("success"):
                                if websocket_send:
                                    await websocket_send({
                                        "type": "artifact",
                                        "name": os.path.basename(t_params.get("path", "file")),
                                        "content": t_params.get("content", ""),
                                        "language": "markdown" if t_params.get("path", "").endswith(".md") else "plaintext"
                                    })

                            # ── FIX 6: Tool-type-aware verification ──
                            original_task = ""
                            for m in self.history:
                                if m.get("role") == "user":
                                    original_task = m.get("content", "")
                                    break

                            if t_name == "file" and t_params.get("action") == "write":
                                result_summary = (
                                    f"File written: {t_params.get('path')}\n"
                                    f"Content preview: {str(t_params.get('content', ''))[:500]}"
                                )
                            elif t_name == "shell":
                                result_summary = (
                                    f"Shell command: {t_params.get('command')}\n"
                                    f"Output: {tool_output[:500]}"
                                )
                            elif t_name == "search":
                                result_summary = (
                                    f"Search: {t_params.get('query')}\n"
                                    f"Results: {tool_output[:500]}"
                                )
                            else:
                                result_summary = f"Tool {t_name} executed. Output: {tool_output[:500]}"

                            verification_prompt = f"""
Original task: {original_task}
Action taken: {result_summary}
Is this action meaningfully progressing toward the task completion?
Reply ONLY with 'CONTINUE' (more steps needed) or 'DONE' (task is complete).
"""
                            verdict_resp = await self.router.generate(
                                messages=[{"role": "user", "content": verification_prompt}],
                                task_hint="quick"
                            )
                            verdict = verdict_resp.get("text", "CONTINUE").upper()
                            if "DONE" in verdict:
                                return {"status": "completed", "result": tool_output, "steps": subtask_results}
                            # else: continue the loop

                            subtask_results.append({
                                "step": step, "action": "tool_call", "tool": t_name,
                                "result": tool_output[:200]
                            })
                    else:
                        return response.get("text", "Done")

                return "Step limit reached"

            if subtask_type in self.tools:
                tool = self.tools[subtask_type]
                await asyncio.sleep(1)
                tool_args = {**subtask.get("params", {})}
                if subtask_type in ["file", "shell", "browser"]:
                    tool_args["session_id"] = self.session_id
                return await tool(**tool_args)

            return {"status": "success", "step": subtask_type}

        except Exception as e:
            logger.error(f"Subtask error: {e}")
            raise

    # ── LEGACY: Error recovery ──

    async def _handle_error_with_recovery(self, task_id: str, error: str,
                                          original_task: str, max_retries: int = 3):
        """Attempt recovery after failure. LEGACY fallback only."""
        from backend.agent.core import ExecutionResult, TaskStatus
        logger.info("RECOVERY: attempting fallback...")

        for attempt in range(max_retries):
            try:
                logger.info(f"RECOVERY: attempt {attempt + 1}/{max_retries}")
                alt_plan = await self._create_alternative_plan(original_task)
                output = await self._execute_plan(task_id, alt_plan)
                return ExecutionResult(
                    task_id=task_id, status=TaskStatus.COMPLETED,
                    output=output, metadata={"recovery_attempt": attempt + 1}
                )
            except Exception as e:
                logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                continue

        return ExecutionResult(
            task_id=task_id, status=TaskStatus.FAILED,
            error=f"Recovery failed: {error}"
        )

    async def _create_alternative_plan(self, task_description: str):
        """Create simplified fallback plan. LEGACY fallback only."""
        from backend.agent.core import TaskPlan
        return TaskPlan(
            task_id=str(uuid.uuid4()),
            description=task_description,
            subtasks=[
                {"type": "analyze", "params": {"task": task_description}},
                {"type": "execute_simple", "params": {"task": task_description}}
            ],
            strategy="sequential"
        )

    async def _decompose_task(self, description: str, complexity: float) -> List[Dict[str, Any]]:
        """Decompose task into subtasks based on complexity."""
        if complexity > 0.7:
            return [
                {"type": "analyze", "params": {"task": description}},
                {"type": "plan", "params": {"task": description}},
                {"type": "execute", "params": {"task": description}},
                {"type": "verify", "params": {"task": description}},
                {"type": "optimize", "params": {"task": description}}
            ]
        elif complexity > 0.4:
            return [
                {"type": "analyze", "params": {"task": description}},
                {"type": "execute", "params": {"task": description}},
                {"type": "verify", "params": {"task": description}}
            ]
        else:
            return [{"type": "execute", "params": {"task": description}}]

    def _synthesize_results(self, results: List[Any]) -> Dict[str, Any]:
        """Synthesize subtask results."""
        return {
            "total_subtasks": len(results),
            "successful": sum(1 for r in results if not isinstance(r, Exception)),
            "failed": sum(1 for r in results if isinstance(r, Exception)),
            "results": results
        }
