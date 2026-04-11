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
    
    ORCHESTRATION_LANGUAGE = "RUSSIAN"
    
    SYSTEM_PROMPT = """
    You are the Executor Agent for Archimedes, a high-performance autonomous assistant.
    Your goal is to complete the current SUBTASK with precision and efficiency.
    
    SUBTASK: {subtask}
    PLAN CONTEXT: {plan}
    
    CORE DIRECTIVES:
    1. LANGUAGE: ALWAYS RESPOND IN RUSSIAN. All thoughts and outputs must be in Russian.
    2. ACTION FIRST: If you have a tool that matches the subtask (e.g., 'mirofish' for simulations, 'search' for info), USE IT IMMEDIATELY. 
    3. MINIMAL RESEARCH: Do not waste time researching the "meaning" of hypothetical or simulated tasks. If the user asks for a simulation or "What if", jump straight to the 'mirofish' tool.
    4. TOOL SPECIFICS:
       - 'search': Use when you lack specific facts or recent data.
       - 'mirofish': Use for ALL simulations, public reactions, and hypothetical scenarios.
       - 'shell/file': Use for technical execution and file management.
    5. THOUGHTS: Keep your reasoning concise. Focus on *what* you are doing next in RUSSIAN.
    
    If the subtask can be answered directly without tools (e.g., simple explanation), provide the answer in plain text in RUSSIAN.
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
            # Preparation for LLM call
            messages = self.context_manager.get_messages()
            
            # If history is empty or doesn't have the system prompt, prepare it
            if not any(m["role"] == "system" for m in messages):
                formatted_prompt = self.SYSTEM_PROMPT.format(
                    subtask=current_target,
                    plan=str(state.current_plan) if state.current_plan else "No formal plan."
                )
                self.context_manager.add_message("system", formatted_prompt)
                messages = self.context_manager.get_messages()

            if not any(m["role"] == "user" for m in messages):
                self.context_manager.add_message("user", current_target)
                messages = self.context_manager.get_messages()

            # Proactive session heartbeat: prevent inactivity reaping during long generations
            try:
                self.tool_registry.sandbox_manager.touch_session(state.session_id)
            except Exception:
                pass

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
                
                # Update shared state history
                state.history = self.context_manager.get_messages()
                
                # UI artifact support
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
                # No more tool calls, subtask finished — send result to user
                res_text = response.get("text", "Готово.")
                
                # Double check language for res_text (simplified)
                if websocket_send and res_text:
                    await websocket_send({"type": "message_result", "content": res_text})
                state.results.append({"step": state.current_step_index, "output": res_text})
                state.history = self.context_manager.get_messages()
                return state
        
        await self.log_info(f"Subtask hit iteration limit ({self.max_steps} steps).", websocket_send)
        state.history = self.context_manager.get_messages()
        return state
