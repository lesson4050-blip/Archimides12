import logging
import uuid
import os
from typing import Optional, Callable, List, Dict, Any
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.models.model_router import ModelRouter
from backend.agent.thought_engine import ThoughtEngine
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager
from backend.config import settings

logger = logging.getLogger(__name__)

class ExecutorAgent(BaseAgent):
    """
    The main execution agent that invokes tools and solves subtasks or entire tasks.
    """
    def __init__(self, router: ModelRouter, tool_registry: ToolRegistry, context_manager: ContextManager):
        super().__init__("Executor", router)
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.max_steps = getattr(settings, "AGENT_MAX_ITERATIONS", 25)

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        # Determine target task: either the whole task (Fast) or the current subtask (Planning)
        if state.mode == AgentMode.FAST:
            current_target = state.task_description
            await self.log_info(f"Executing task in FAST mode...", websocket_send)
        else:
            # Planning mode: execute the current step/subtask
            if not state.current_plan:
                 await self.log_info("Executing task without a formal plan...", websocket_send)
                 current_target = state.task_description
            else:
                phases = state.current_plan.get("phases", [])
                # For simplicity, we assume linear progression through phases and subtasks
                # This could be more complex in a real multi-agent system
                current_target = f"Subtask: {state.task_description}" # Default fallback
                found = False
                total_steps = 0
                for phase in phases:
                    for subtask in phase.get("subtasks", []):
                        if total_steps == state.current_step_index:
                            current_target = subtask.get("description", state.task_description)
                            found = True
                            break
                        total_steps += 1
                    if found: break
                
                await self.log_info(f"Executing step {state.current_step_index + 1}: {current_target}", websocket_send)

        # Loop for tool execution
        for step in range(self.max_steps):
            # Sync context manager with shared history
            # (In a real system, we'd only sync once per process call)
            
            # Preparation for LLM call
            messages = self.context_manager.get_messages()
            # If history is empty, add system prompt and target
            if not any(m["role"] == "user" for m in messages):
                self.context_manager.add_message("user", current_target)
                messages = self.context_manager.get_messages()

            # Model iteration
            response = await self.router.generate(
                messages=messages,
                tools=self.tool_registry.get_all_tool_definitions(),
                task_hint="think"
            )

            thought = response.get("thought", "")
            if thought:
                await self.log_thought(thought, websocket_send)
            
            tool_call = response.get("tool_call")
            if tool_call:
                t_name = tool_call["name"]
                t_params = tool_call["params"]
                
                # Register tool call in state/history
                call_id = f"call_{str(uuid.uuid4())[:8]}"
                std_tool_call = {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": t_name,
                        "arguments": t_params
                    }
                }
                
                # Execute tool
                tool_res = await self.tool_registry.execute_tool(
                    t_name, 
                    t_params, 
                    session_id=state.session_id
                )
                
                # Extract output
                success = tool_res.get("success", True)
                output = str(tool_res.get("output", tool_res.get("content", "OK")))
                if not success:
                    output = f"ERROR: {tool_res.get('error', 'Unknown error')}"

                # Add to history
                self.context_manager.add_message("assistant", thought or "", tool_calls=[std_tool_call])
                self.context_manager.add_message("tool", output, tool_call_id=call_id, name=t_name)
                
                # Check for final result tool
                if t_name == "message" and t_params.get("type") == "result":
                    state.results.append({"step": state.current_step_index, "output": t_params.get("content", "")})
                    # Sync back to shared state
                    state.history = self.context_manager.get_messages()
                    return state

                # Update shared state history
                state.history = self.context_manager.get_messages()
                
                # UI artifact support (simplified)
                if t_name == "file" and t_params.get("action") == "write" and success:
                    if websocket_send:
                        await websocket_send({
                            "type": "artifact",
                            "name": os.path.basename(t_params.get("path", "file")),
                            "content": t_params.get("content", ""),
                            "language": "markdown" if t_params.get("path", "").endswith(".md") else "plaintext"
                        })
                
                # Periodically summarize if needed
                await self.context_manager.summarize_if_needed(self.router)
            else:
                # No more tool calls, subtask finished
                res_text = response.get("text", "Done.")
                state.results.append({"step": state.current_step_index, "output": res_text})
                state.history = self.context_manager.get_messages()
                return state
        
        await self.log_info(f"Subtask hit iteration limit ({self.max_steps} steps).", websocket_send)
        state.history = self.context_manager.get_messages()
        return state
