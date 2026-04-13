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
    You are the Executor Agent for Archimedes. 
    Your goal is to solve the SUBTASK with extreme precision and high-quality results.
    
    SUBTASK: {subtask}
    PLAN CONTEXT: {plan}
    TASK MODE: {task_hint}
    
    CORE DIRECTIVES:
    1. LANGUAGE: ALWAYS RESPOND IN RUSSIAN. All thoughts and final answers must be in Russian.
    2. STYLE: Be professional, helpful, and conversational in your final responses.
    3. STEERING: 
       {hint_instructions}
    4. ACTION: If tools are needed, use them immediately. Don't over-explain if a tool can do the job.
    
    When you have completed the subtask, provide a polite and clear summary of your work in RUSSIAN.
    """

    def __init__(self, router: ModelRouter, tool_registry: ToolRegistry, context_manager: ContextManager):
        super().__init__("Executor", router)
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.max_steps = getattr(settings, "AGENT_MAX_ITERATIONS", 25)

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        # Determine target task
        if state.mode == AgentMode.FAST:
            current_target = state.task_description
            await self.log_info(f"Исполнение задачи (Быстрый режим)...", websocket_send)
        else:
            if not state.current_plan:
                 current_target = state.task_description
            else:
                phases = state.current_plan.get("phases", [])
                current_target = state.task_description
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
                
                await self.log_info(f"Шаг {state.current_step_index + 1}: {current_target}", websocket_send)

        # Steering instructions
        hint_instructions = "Operate normally."
        if state.task_hint == "search":
            hint_instructions = "RESEARCH MODE: Exhaust all search possibilities. Don't settle for the first result. Synthesize multiple sources into a deep, structured report."
        elif state.task_hint == "plan":
            hint_instructions = "PRESENTATION MODE: You are a slide designer. Focus on structured content, clear headings, and visual appeal. Use the 'slides' tool for final output."
        elif state.task_hint == "execute":
            hint_instructions = "DEVELOPER MODE: Focus on writing clean, functional code or documents. Use 'shell' and 'file' tools aggressively. Verify your work with tests if possible."

        # Loop for tool execution
        for step in range(self.max_steps):
            messages = self.context_manager.get_messages()
            
            if not any(m["role"] == "system" for m in messages):
                formatted_prompt = self.SYSTEM_PROMPT.format(
                    subtask=current_target,
                    plan=str(state.current_plan) if state.current_plan else "No formal plan.",
                    task_hint=state.task_hint,
                    hint_instructions=hint_instructions
                )
                self.context_manager.add_message("system", formatted_prompt)
                messages = self.context_manager.get_messages()

            if not any(m["role"] == "user" for m in messages):
                self.context_manager.add_message("user", current_target)
                messages = self.context_manager.get_messages()

            try:
                from backend.sandbox.singleton import sandbox_manager
                sandbox_manager.touch_session(state.session_id)
            except Exception:
                pass

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
                
                call_id = f"call_{str(uuid.uuid4())[:8]}"
                std_tool_call = {
                    "id": call_id,
                    "type": "function",
                    "function": { "name": t_name, "arguments": t_params }
                }
                
                tool_res = await self.tool_registry.execute_tool(t_name, t_params, session_id=state.session_id)
                success = tool_res.get("success", True)
                output = str(tool_res.get("output", tool_res.get("content", "OK")))
                if not success:
                    output = f"ERROR: {tool_res.get('error', 'Unknown error')}"

                self.context_manager.add_message("assistant", thought or "", tool_calls=[std_tool_call])
                self.context_manager.add_message("tool", output, tool_call_id=call_id, name=t_name)
                state.history = self.context_manager.get_messages()
                
                if t_name == "file" and t_params.get("action") == "write" and success:
                    if websocket_send:
                        await websocket_send({
                            "type": "artifact",
                            "name": os.path.basename(t_params.get("path", "file")),
                            "content": t_params.get("content", ""),
                            "language": "markdown" if t_params.get("path", "").endswith(".md") else "plaintext"
                        })
                
                await self.context_manager.summarize_if_needed(self.router)
                # CONTINUE the loop to process tool output
                continue
            else:
                # No tool call — this is the final answer for this subtask
                res_text = response.get("text", "")
                if not res_text and step == 0:
                    res_text = "Я выполнил эту часть задачи." # Safety fallback
                
                if websocket_send and res_text:
                    await websocket_send({"type": "message_result", "content": res_text})
                
                state.results.append({"step": state.current_step_index, "output": res_text or "Done."})
                state.history = self.context_manager.get_messages()
                return state
        
        await self.log_info(f"Subtask hit iteration limit ({self.max_steps} steps).", websocket_send)
        state.history = self.context_manager.get_messages()
        return state
