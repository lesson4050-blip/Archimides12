import logging
import uuid
import os
from typing import Optional, Callable
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.models.model_router import ModelRouter
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
    
    PRESENTATION GENERATION (MANDATORY RULES):
    - For ANY request about "презентация", "слайды", "pitch deck",
      "deck", "presentation" → ALWAYS use the presentation tool.
    - NEVER try to generate slides with file tool or shell tool.
    - presentation tool produces Gamma/Kimi quality PPTX automatically.
    - Default: slide_count=8, theme="dark", language="ru"
    - For business pitch: theme="corporate", slide_count=10
    - For education: theme="light", slide_count=12
    - For creative topics: theme="bold" or "gradient"
    - After generation: share the file with user and open preview
    - The tool handles everything — just call it with a good prompt.
    
    When you have completed the subtask, provide a polite and clear summary of your work in RUSSIAN.{memory_context}
    """

    def __init__(self, router: ModelRouter, tool_registry: ToolRegistry, context_manager: ContextManager):
        super().__init__("Executor", router)
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.max_steps = getattr(settings, "AGENT_MAX_ITERATIONS", 25)

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        # Clear previous critic verdict to prevent cross-subtask pollution
        state.metadata.pop("critic_verdict", None)
        state.metadata.pop("critic_scores", None)
        state.metadata.pop("critic_issues", None)
        
        # Determine target task
        if state.mode == AgentMode.FAST:
            current_target = state.task_description
            await self.log_info("Исполнение задачи (Быстрый режим)...", websocket_send)
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

        # Track previous error for self-improvement
        prev_error = None

        # Loop for tool execution
        for step in range(self.max_steps):
            # Loop detection
            if not hasattr(state, '_recent_tool_calls'):
                state._recent_tool_calls = []
            if len(state._recent_tool_calls) >= 3:
                last3 = state._recent_tool_calls[-3:]
                if len(set(last3)) == 1:
                    self.context_manager.add_message("user",
                        "SYSTEM: You are repeating the same action. "
                        "Try a completely different approach or call "
                        "message(type='result') with what you have.")
                    state._recent_tool_calls = []

            messages = self.context_manager.get_messages_with_cache()
            
            if not any(m["role"] == "system" for m in messages):
                # Inject relevant memory bank context
                from backend.memory.memory_bank import (
                    get_relevant_facts, get_session_summary
                )
                from backend.memory.knowledge_graph import format_graph_context

                memory_facts = get_relevant_facts(limit=5)

                # Get summary of last session for continuity
                last_session_facts = get_relevant_facts(limit=3, category="task_result")

                # Extract key terms from task for graph query
                task_words = current_target.split()[:4]
                key_term = " ".join(task_words) if task_words else ""
                graph_ctx = format_graph_context(key_term, depth=2) if key_term else ""

                memory_context = ""
                if memory_facts:
                    memory_context += (
                        "\n\nMEMORY BANK:\n"
                        + "\n".join(f"• {f}" for f in memory_facts)
                    )
                if last_session_facts:
                    memory_context += (
                        "\n\nLAST SESSION LEARNINGS:\n"
                        + "\n".join(f"→ {f}" for f in last_session_facts)
                    )
                if graph_ctx:
                    memory_context += f"\n\n{graph_ctx}"

                formatted_prompt = self.SYSTEM_PROMPT.format(
                    subtask=current_target,
                    plan=str(state.current_plan) if state.current_plan else "No formal plan.",
                    task_hint=state.task_hint,
                    hint_instructions=hint_instructions,
                    memory_context=memory_context
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

            # Section 2B: Support streaming mode
            use_stream = getattr(state, 'stream', False)
            if use_stream:
                # Proper async wrapper for streaming callback
                async def _stream_token(t):
                    if websocket_send:
                        await websocket_send(t)

                response = await self.router.generate_stream(
                    messages=messages,
                    tools=self.tool_registry.get_all_tool_definitions(),
                    task_hint="think",
                    on_token=_stream_token
                )
            else:
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
                state._recent_tool_calls.append(str(t_name) + str(t_params))

                
                call_id = f"call_{str(uuid.uuid4())[:8]}"
                std_tool_call = {
                    "id": call_id,
                    "type": "function",
                    "function": { "name": t_name, "arguments": t_params }
                }
                
                tool_res = await self.tool_registry.execute_tool(t_name, t_params, session_id=state.session_id)
                
                from backend.utils.structured_logger import log_model_response
                log_model_response(
                    state.session_id,
                    response.get("model_used", "unknown"),
                    had_tool_call=True,
                    tokens=response.get("tokens_used", 0)
                )

                success = tool_res.get("success", True)
                output = str(tool_res.get("output", tool_res.get("content", "OK")))
                if not success:
                    output = f"ERROR: {tool_res.get('error', 'Unknown error')}"
                    prev_error = output  # Track for self-improvement

                    # Track confidence: failure drops score
                    if not hasattr(state, 'confidence_score'):
                        state.confidence_score = 100
                    state.confidence_score = max(0, state.confidence_score - 15)
                    
                    # Section 6A: Check self-improvement DB for known fix
                    from backend.agent.self_improvement import get_fix_hint
                    fix_hint = get_fix_hint(output)
                    if fix_hint:
                        output += f"\n[LEARNED FIX]: {fix_hint}"
                        await self.log_thought(
                            f"💡 Applied learned fix pattern", websocket_send
                        )
                    
                    if "not found" in output.lower() or "missing" in output.lower():
                        # Try auto-tooling
                        try:
                            from backend.mcp_hub.auto_tooling import find_and_connect_tool
                            from backend.sandbox.singleton import sandbox_manager

                            # BUG 1: Get mcp_client from agent core via singleton
                            from backend.websocket.handler import manager as ws_manager
                            agent = ws_manager.agent_loops.get(state.session_id)
                            mcp_client = getattr(agent, 'mcp_client', None) if agent else None

                            new_tool = await find_and_connect_tool(
                                task_description=state.task_description,
                                available_tools=list(self.tool_registry.tools.keys()),
                                mcp_client=mcp_client,
                                executor=sandbox_manager.executor,
                                session_id=state.session_id,
                                router=self.router
                            )
                            if new_tool:
                                await self.log_info(
                                    f"🔌 Auto-connected tool: {new_tool}", websocket_send
                                )
                                output += f"\n(Auto-tooling installed: {new_tool}. Try again!)"
                        except Exception as e:
                            logger.warning(f"Auto-tooling attempt failed: {e}")
                else:
                    # Section 6A: Learn from successful recovery
                    if prev_error and success:
                        from backend.agent.self_improvement import learn_from_error
                        learn_from_error(
                            error=prev_error,
                            fix=f"Used {t_name} with {t_params}",
                            tool_name=t_name
                        )
                        prev_error = None

                    # Track confidence: success increases score
                    if not hasattr(state, 'confidence_score'):
                        state.confidence_score = 100
                    state.confidence_score = min(100, state.confidence_score + 5)

                    # Send confidence to frontend periodically
                    if websocket_send and step % 3 == 0:
                        score = getattr(state, 'confidence_score', 100)
                        await websocket_send({
                            "type": "confidence",
                            "score": score,
                            "label": (
                                "🟢 Уверен" if score > 70
                                else "🟡 Осторожно" if score > 40
                                else "🔴 Затрудняюсь"
                            )
                        })

                self.context_manager.add_message("assistant", thought or "", tool_calls=[std_tool_call])
                self.context_manager.add_message("tool", output, tool_call_id=call_id, name=t_name)
                state.history = self.context_manager.get_messages()
                
                # Extract knowledge from tool results
                if success and len(output) > 100:
                    import asyncio
                    from backend.memory.knowledge_graph import extract_and_store_knowledge
                    asyncio.create_task(
                        extract_and_store_knowledge(
                            output[:500],
                            state.session_id,
                            self.router
                        )
                    )
                    
                
                if t_name == "file" and t_params.get("action") == "write" and success:
                    content = t_params.get("content", "")
                    path = t_params.get("path", "")

                    # BUG 2: Apply TDD for code files in execute mode — pass actual code
                    if (path.endswith((".py", ".js", ".ts")) and
                        len(content) > 50 and
                        state.task_hint == "execute"):
                        try:
                            from backend.agent.tdd_executor import TDDExecutor
                            from backend.sandbox.singleton import sandbox_manager
                            tdd = TDDExecutor(self.router, sandbox_manager.executor)
                            tdd_result = await tdd.execute_tdd(
                                task=state.task_description,
                                initial_code=content,      # Pass the actual written code!
                                code_path=path,
                                session_id=state.session_id,
                                websocket_send=websocket_send
                            )
                            if "[TDD Success]" in tdd_result:
                                output += f"\n✅ TDD: verified successfully"
                        except Exception as tdd_err:
                            logger.warning(f"TDD failed (non-critical): {tdd_err}")

                    if websocket_send:
                        await websocket_send({
                            "type": "artifact",
                            "name": os.path.basename(path or "file"),
                            "content": content,
                            "language": "markdown" if path.endswith(".md") else "plaintext"
                        })
                
                # COSMO Presentation file artifact
                if t_name == "presentation" and success:
                    file_path = tool_res.get("file_path", "")
                    filename = tool_res.get("filename", "presentation.pptx")
                    preview_url = tool_res.get("preview_url", "")
            
                    if file_path and os.path.exists(file_path):
                        # Read file and send as base64 artifact
                        import base64
                        with open(file_path, "rb") as f:
                            pptx_bytes = f.read()
                        b64 = base64.b64encode(pptx_bytes).decode()
            
                        if websocket_send:
                            # Send downloadable file artifact
                            await websocket_send({
                                "type": "file_artifact",
                                "filename": filename,
                                "mime_type": (
                                    "application/vnd.openxmlformats-"
                                    "officedocument.presentationml.presentation"
                                ),
                                "data": b64,
                                "size_kb": tool_res.get("file_size_kb", 0),
                                "preview_url": preview_url,
                                "label": "⚡ COSMO Presentation"
                            })
            
                            # Also send preview in browser tab if preview_url exists
                            if preview_url:
                                await websocket_send({
                                    "type": "browser_navigate",
                                    "url": preview_url,
                                    "title": "COSMO Presentation Preview"
                                })
                
                await self.context_manager.summarize_if_needed(self.router)
                # CONTINUE the loop to process tool output
                continue
            else:
                # No tool call — this is the final answer for this subtask
                res_text = response.get("text", "")
                
                # If model returned nothing useful after first step, nudge it
                if not res_text and step > 0 and step < self.max_steps - 1:
                    self.context_manager.add_message(
                        "user",
                        "Continue with the task. Use a tool or provide "
                        "the final answer."
                    )
                    continue

                if not res_text and step == 0:
                    res_text = "Я выполнил эту часть задачи." # Safety fallback
                
                if websocket_send and res_text:
                    await websocket_send({"type": "message_info", "content": f"Результат шага: {res_text}"})
                
                state.results.append({"step": state.current_step_index, "output": res_text or "Done."})
                
                # Save key learnings to Memory Bank
                if res_text and len(res_text) > 100:
                    try:
                        from backend.memory.memory_bank import save_fact

                        # Ask the model to extract key facts from this result
                        extract_prompt = (
                            f"Extract 1-2 key facts or rules learned from this task "
                            f"result. Be very concise, max 100 chars each. "
                            f"Output as JSON array of strings: "
                            f'["fact1", "fact2"]\n\nResult: {res_text[:500]}'
                        )
                        extract_resp = await self.router.generate(
                            messages=[{"role": "user", "content": extract_prompt}],
                            task_hint="think"
                        )
                        from backend.utils.json_repair import repair_and_parse
                        facts_raw = extract_resp.get("text", "")
                        facts, _ = repair_and_parse(facts_raw)
                        if isinstance(facts, list):
                            for fact in facts[:2]:
                                if isinstance(fact, str) and len(fact) > 5:
                                    save_fact(
                                        fact=fact,
                                        session_id=state.session_id,
                                        category="task_result",
                                        importance=2
                                    )
                    except Exception as e:
                        logger.warning(f"Memory Bank write failed (non-critical): {e}")

                state.history = self.context_manager.get_messages()

                # Proactive next-step suggestion
                if res_text and len(res_text) > 100:
                    try:
                        suggest_prompt = (
                            f"Task completed: {state.task_description}\n"
                            f"Result: {res_text[:300]}\n\n"
                            f"Suggest 2-3 logical NEXT STEPS the user might want. "
                            f"Output as short JSON array: "
                            f'["action1", "action2", "action3"]\n'
                            f"Max 8 words each. In RUSSIAN."
                        )
                        sug_resp = await self.router.generate(
                            messages=[{"role": "user", "content": suggest_prompt}],
                            task_hint="think"
                        )
                        from backend.utils.json_repair import repair_and_parse as _rp
                        suggestions, _ = _rp(sug_resp.get("text", ""))
                        if isinstance(suggestions, list) and suggestions:
                            if websocket_send:
                                await websocket_send({
                                    "type": "suggestions",
                                    "items": suggestions[:3]
                                })
                    except Exception:
                        pass  # Non-critical

                return state
        
        await self.log_info(f"Subtask hit iteration limit ({self.max_steps} steps).", websocket_send)
        state.history = self.context_manager.get_messages()
        return state
