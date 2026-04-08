import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from backend.models.model_router import ModelRouter
from backend.agent.thought_engine import ThoughtEngine
from backend.agent.tool_registry import ToolRegistry
from backend.agent.planner import PlanManager
from backend.agent.error_recovery import ErrorRecovery
from backend.agent.skills import SkillManager
from backend.memory.context_manager import ContextManager
from backend.memory.vector_store import VectorStore
from backend.sandbox.singleton import sandbox_manager

# Tools
from backend.tools.shell_tool import ShellTool
from backend.tools.file_tool import FileTool
from backend.tools.browser_tool import BrowserTool
from backend.tools.search_tool import SearchTool
from backend.tools.plan_tool import PlanTool
from backend.tools.message_tool import MessageTool
from backend.tools.expose_tool import ExposeTool
from backend.tools.schedule_tool import ScheduleTool
from backend.tools.slides_tool import SlidesTool
from backend.tools.webdev_tool import WebDevTool
from backend.config import settings

logger = logging.getLogger(__name__)

class AgentLoop:
    """
    The core execution engine of Archemidas.
    Runs the Analyze → Think → Select Tool → Execute → Observe → Iterate cycle.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.router = ModelRouter()
        self.thought_engine = ThoughtEngine()
        self.tool_registry = ToolRegistry()
        self.plan_manager = PlanManager(self.session_id)
        self.error_recovery = ErrorRecovery()
        self.context_manager = ContextManager()
        self.vector_store = VectorStore(session_id)
        
        # Sandbox / Execution
        self.sandbox = sandbox_manager
        self.executor = self.sandbox.executor
        self.filesystem = self.sandbox.filesystem
        
        # Register Tools
        self.tool_registry.register("shell", ShellTool(self.executor))
        self.tool_registry.register("file", FileTool(self.filesystem))
        self.tool_registry.register("browser", BrowserTool(self.executor))
        self.tool_registry.register("search", SearchTool())
        self.tool_registry.register("plan", PlanTool(self.plan_manager))
        self.tool_registry.register("message", MessageTool())
        self.tool_registry.register("expose", ExposeTool(self.executor))
        self.tool_registry.register("schedule", ScheduleTool())
        self.tool_registry.register("slides", SlidesTool())
        self.tool_registry.register("webdev", WebDevTool(self.executor, self.filesystem))
        
        # Skill Manager
        self.skill_manager = SkillManager(self.tool_registry)
        self.tool_registry.register("skill", self.skill_manager)
        
        self.history: List[Dict[str, Any]] = []
        self.system_prompt = ThoughtEngine.get_system_prompt()
        self.max_iterations = settings.AGENT_MAX_ITERATIONS
        self.current_iteration = 0
        self.plan: List[Dict[str, Any]] = []
        self.is_running = False

    async def run(self, task: str, websocket_send: Optional[Callable] = None) -> None:
        self.is_running = True
        self.current_iteration = 0
        
        # Initialize history with system prompt
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.history.append({"role": "user", "content": task})
        
        while self.current_iteration < self.max_iterations and self.is_running:
            self.current_iteration += 1
            logger.info(f"Iteration {self.current_iteration} for session {self.session_id}")
            
            # 1. ANALYZE & THINK
            # We determine task hint based on history or context (simplified)
            task_hint = "default"
            if self.current_iteration == 1:
                task_hint = "plan"
            
            try:
                response = await self.router.generate(
                    messages=self.history,
                    tools=self.tool_registry.get_all_tool_definitions(),
                    task_hint=task_hint
                )
            except Exception as e:
                logger.error(f"Error in model generation: {e}")
                if websocket_send:
                    await websocket_send({
                        "type": "agent_error",
                        "message": str(e),
                        "iteration": self.current_iteration,
                        "retrying": False
                    })
                break
            
            # 2. STREAM THOUGHT
            thought = response.get("thought", "")
            if thought and websocket_send:
                await websocket_send({
                    "type": "thought",
                    "content": thought,
                    "streaming": False,
                    "iteration": self.current_iteration
                })
            
            # 3. SELECT & EXECUTE TOOL
            tool_call = response.get("tool_call")
            if tool_call:
                tool_name = tool_call["name"]
                tool_params = tool_call["params"]
                
                if websocket_send:
                    await websocket_send({
                        "type": "tool_call",
                        "tool": tool_name,
                        "params": tool_params,
                        "iteration": self.current_iteration
                    })
                
                # Execute tool
                result = await self.tool_registry.execute_tool(tool_name, tool_params, session_id=self.session_id)
                
                # 4. OBSERVE
                # Formats vary by model, but we'll use a standard format for internal storage
                # Mandatory for Groq/OpenAI: tool_calls must have an id and type
                tool_call_id = tool_call.get("id") or f"call_{self.current_iteration}_{datetime.now().timestamp()}"
                
                # Assistant message with tool calls
                self.history.append({
                    "role": "assistant",
                    "content": response.get("text", ""),
                    "tool_calls": [{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_params # Passed as dict for Pydantic/OpenAI compliance
                        }
                    }]
                })
                
                # Tool result message
                raw_output = str(result.get("output", result.get("error", "No output")))
                if len(raw_output) > 2000:
                    raw_output = raw_output[:2000] + "\n...[output truncated, too large]"
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": raw_output
                })
                
                if websocket_send:
                    await websocket_send({
                        "type": "tool_result",
                        "tool": tool_name,
                        "output": str(result.get("output", "")),
                        "error": result.get("error"),
                        "success": result.get("success", True),
                        "iteration": self.current_iteration
                    })
                    
                if tool_name == "plan" and websocket_send:
                    await websocket_send({
                        "type": "plan_update",
                        "phases": self.plan_manager.phases,
                        "iteration": self.current_iteration
                    })
                
                # Special case: if message(type="result"), we are done
                if tool_name == "message" and tool_params.get("type") == "result":
                    logger.info("Task completed via result message.")
                    if websocket_send and self.plan_manager.phases:
                        for phase in self.plan_manager.phases:
                            phase["status"] = "complete"
                        await websocket_send({
                            "type": "plan_update",
                            "phases": self.plan_manager.phases,
                            "iteration": self.current_iteration
                        })
                    self.is_running = False
                    break
                    
                # Special case: if message(type="ask"), pause and wait for user
                if tool_name == "message" and tool_params.get("type") == "ask":
                    logger.info("Agent is asking user. Waiting for response...")
                    self.is_running = False
                    break

            else:
                # No tool call, just text
                text = response.get("text", "")
                self.history.append({"role": "assistant", "content": text})
                if websocket_send:
                    await websocket_send({
                        "type": "message_info",
                        "text": text,
                        "iteration": self.current_iteration
                    })
                # If no tool call, we break to avoid multiple responses to a single user message (e.g. greetings)
                break

            # 5. CONTEXT MANAGEMENT
            self.context_manager.history = self.history
            self.context_manager.current_tokens = sum(
                len(str(m.get("content", ""))) for m in self.history
            ) // 4
            await self.context_manager.summarize_if_needed(self.router)
            self.history = self.context_manager.history

        if self.current_iteration >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached.")
            if websocket_send:
                await websocket_send({
                    "type": "session_end",
                    "reason": "max_iterations"
                })
        
        self.is_running = False
        logger.info(f"Agent loop finished for session {self.session_id}")
