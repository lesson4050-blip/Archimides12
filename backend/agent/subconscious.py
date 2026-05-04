import asyncio
import logging
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SubconsciousEngine:
    """
    Archimedes Zero-Latency Subconscious Engine.
    
    This module decouples the main LLM thought loop from heavy I/O tasks.
    It runs predictive pre-fetching, background linting, and automated
    documentation retrieval *before* the agent officially requests it.
    """
    
    def __init__(self, router, tool_registry, event_bus=None):
        self.router = router
        self.tool_registry = tool_registry
        self.event_bus = event_bus
        self._background_tasks = set()
        
    def _track_task(self, task: asyncio.Task):
        """Keep strong references to background tasks to prevent GC."""
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def trigger_predictive_analysis(self, current_thought: str, session_id: str):
        """
        Spawns a background thread that analyzes the agent's current thought
        and pre-emptively executes tools it suspects the agent will need next.
        """
        task = asyncio.create_task(self._predictive_loop(current_thought, session_id))
        self._track_task(task)

    def trigger_auto_tdd(self, file_path: str, session_id: str):
        """
        Triggered when the agent writes to a file. Runs tests/linting immediately
        and injects the result into the EventBus so it's ready before the agent asks.
        """
        task = asyncio.create_task(self._run_auto_tdd(file_path, session_id))
        self._track_task(task)

    async def _predictive_loop(self, thought: str, session_id: str):
        """LLM-based prediction of next required context."""
        try:
            # We use a fast, cheap model to guess the next tool call
            prompt = (
                f"The agent is currently thinking: '{thought}'\n"
                f"What information or file does it likely need next? "
                f"Reply ONLY with a tool name and query, e.g., 'search: python asyncio tutorial' "
                f"or 'file_view: main.py'. If nothing obvious, reply 'NONE'."
            )
            resp = await self.router.generate([{"role": "user", "content": prompt}], task_hint="quick")
            prediction = resp.get("text", "NONE").strip()
            
            if prediction != "NONE" and ":" in prediction:
                logger.info(f"🧠 Subconscious prediction: {prediction}")
                action, target = prediction.split(":", 1)
                action = action.strip().lower()
                target = target.strip()
                
                # Execute the pre-fetch
                result_data = None
                if action == "search" and "search" in self.tool_registry.tools:
                    res = await self.tool_registry.tools["search"](query=target)
                    result_data = res.get("output", "Search failed")
                elif action == "file_view" and "file" in self.tool_registry.tools:
                    res = await self.tool_registry.tools["file"](action="read", path=target, session_id=session_id)
                    result_data = res.get("content", f"Failed to read {target}")
                
                if result_data and self.event_bus:
                    # Inject into the agent's awareness stream
                    preview = result_data[:200].replace('\n', ' ')
                    await self.event_bus.emit_thought(
                        f"Subconscious pre-fetch [{action}]: {preview}...",
                        agent="subconscious"
                    )
                    
        except Exception as e:
            logger.debug(f"Subconscious prediction failed silently: {e}")

    async def _run_auto_tdd(self, file_path: str, session_id: str):
        """Run syntax checks or tests in the background."""
        if not file_path.endswith(".py"):
            return
            
        try:
            if "shell" not in self.tool_registry.tools:
                return
                
            import shlex
            safe_path = shlex.quote(file_path)
            cmd = f"python -m py_compile {safe_path}"
            res = await self.tool_registry.tools["shell"](command=cmd, session_id=session_id)
            
            if res.get("success") is False or res.get("output", "").strip():
                error_msg = res.get("output", res.get("error", "Unknown error"))
                logger.warning(f"🧠 Subconscious Auto-TDD caught error in {file_path}: {error_msg}")
                if self.event_bus:
                    await self.event_bus.emit_error(
                        f"Auto-TDD Alert: Syntax error detected in {file_path}:\n{error_msg}",
                        source="subconscious"
                    )
            else:
                logger.info(f"🧠 Subconscious Auto-TDD passed for {file_path}")
        except Exception as e:
            logger.debug(f"Subconscious Auto-TDD failed: {e}")
