import logging
import re
import asyncio
from typing import Optional, Callable, Dict, Any, List, Tuple
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.agent.orchestration.agents.planner_agent import PlannerAgent
from backend.agent.orchestration.agents.executor_agent import ExecutorAgent
from backend.agent.orchestration.agents.critic_agent import CriticAgent
from backend.agent.orchestration.mcts import MCTSManager
from backend.models.model_router import ModelRouter
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

logger = logging.getLogger(__name__)

# Simple patterns that don't need planning or critic review
CONVERSATIONAL_PATTERNS = [
    r"^(привет|здравствуй|хай|hi|hello|hey|добрый\s+(день|вечер|утро))[\s!.?]*$",
    r"^(как\s+дела|что\s+ты\s+умеешь|кто\s+ты|что\s+ты\s+такое|помо(щь|ги))[\s!.?]*$",
    r"^(спасибо|пока|до\s+свидания|bye|thanks|thank\s+you)[\s!.?]*$",
]

def is_conversational(text: str) -> bool:
    """Check if the task is a simple conversational message (greeting, etc.)."""
    cleaned = text.strip().lower()
    # Very short messages are likely conversational
    if len(cleaned) < 15 and not any(c in cleaned for c in ["/", "\\", "{", "}", "http"]):
        for pattern in CONVERSATIONAL_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return True
    return False


# Semantic routing — maps task intent to agent strategy
ROUTING_RULES = [
    # (pattern, complexity, strategy)
    (r"(write|create|implement|build|code|script|function|class|api|endpoint)",
     "complex", "swarm_code"),
    (r"(research|find|search|analyze|compare|summarize|report|study)",
     "complex", "swarm_research"),
    (r"(present|slide|deck|pitch|визуал|presentation)",
     "complex", "single_slides"),
    (r"(debug|fix|error|bug|broken|не работает|исправь)",
     "complex", "swarm_code"),
    (r"(design|architect|system|structure|план|architecture)",
     "complex", "swarm_architect"),
    (r"(explore|mcts|hypothesis|multiple solutions|branch|эксперимент|альтернатив)",
     "complex", "mcts"),
    (r"(translate|переведи|перевод)",
     "medium", "single"),
    (r"(calculate|посчитай|вычисли|\d+[\+\-\*\/]\d+)",
     "simple", "direct"),
    # Russian complex keywords
    (r"(создай|напиши код|проанализируй|исследуй|сделай сайт|автоматизируй|скрапь|разработай)",
     "complex", "swarm_code"),
]


def classify_task(text: str) -> Tuple[str, str]:
    """
    Returns (complexity, strategy) using multi-signal classification.
    
    Signal 1: Regex pattern match (fast path for obvious cases)
    Signal 2: Multi-signal heuristic for ambiguous cases
    """
    text_lower = text.lower().strip()
    
    # Ultra-short messages are always direct
    if len(text_lower) < 15:
        return "simple", "direct"
    
    # Signal 1: Regex pattern match
    for pattern, complexity, strategy in ROUTING_RULES:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return complexity, strategy
    
    # Signal 2: Multi-signal heuristic for unmatched tasks
    signals = {
        "has_code_markers": bool(re.search(
            r'[{}\[\]();=]|```|def |class |import |function |const |var ',
            text
        )),
        "has_tool_keywords": bool(re.search(
            r'(файл|file|запуст|run|выполн|exec|установ|install|pip |npm )',
            text_lower
        )),
        "has_url": bool(re.search(r'https?://', text)),
        "is_question": text_lower.rstrip().endswith('?') or text_lower.startswith(('что ', 'как ', 'где ', 'why ', 'how ', 'what ')),
        "is_long": len(text_lower) > 150,
        "is_medium": len(text_lower) > 50,
        "has_multiple_steps": bool(re.search(
            r'(\d+[\.\)]\s|\bа также\b|\bи потом\b|\bthen\b|\bafter that\b|шаг\s*\d)',
            text_lower
        )),
    }
    
    complexity_score = sum([
        signals["has_code_markers"] * 3,
        signals["has_tool_keywords"] * 2,
        signals["has_url"] * 1,
        signals["is_long"] * 2,
        signals["is_medium"] * 1,
        signals["has_multiple_steps"] * 3,
    ])
    
    if complexity_score >= 5:
        return "complex", "swarm_code"
    elif complexity_score >= 3 or signals["is_medium"]:
        return "medium", "single"
    elif signals["is_question"]:
        return "simple", "direct"
    else:
        return "simple", "direct"


# Strategy to swarm agent types mapping
STRATEGY_AGENTS = {
    "swarm_code": ["coder", "critic", "tester"],
    "swarm_research": ["researcher", "critic"],
    "swarm_architect": ["architect", "coder", "critic"],
    "single": None,
    "single_slides": None,
    "direct": None,
    "mcts": None,
}


class AgentOrchestrator:
    """
    Coordinates the multi-agent flow: Planner -> Executor -> Critic.
    Also handles the 'Fast' mode vs 'Planning' mode logic.
    """
    def __init__(self, 
                 router: ModelRouter, 
                 tool_registry: ToolRegistry, 
                 context_manager: ContextManager):
        self.router = router
        self.tool_registry = tool_registry
        self.planner = PlannerAgent(router)
        self.executor = ExecutorAgent(router, tool_registry, context_manager)
        self.critic = CriticAgent(router)
        from backend.agent.orchestration.swarm import MicroAgentSwarm
        self.swarm = MicroAgentSwarm(router, tool_registry=tool_registry)
        self.mcts_manager = MCTSManager(workspace_dir=".")
        
    async def run_task(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None,
                       task_hint: str = "default",
                       stream: bool = False) -> Dict[str, Any]:
        
        # Initialize state
        state = OrchestrationState(
            session_id=session_id,
            task_description=task_description,
            mode=mode,
            task_hint=task_hint,
            stream=stream,
        )
        
        # Add initial greeting/task to history
        state.add_message("user", task_description)
        
        # Shortcut: conversational messages get answered directly without planning/critic
        if is_conversational(task_description):
            logger.info(f"[{session_id}] Detected conversational message, using direct response")
            return await self._run_conversational(state, websocket_send)
        
        # Semantic task routing
        complexity, strategy = classify_task(task_description)
        
        if complexity == "simple":
            logger.info(f"[{session_id}] Simple task → fast mode (strategy: {strategy})")
            return await self._run_fast_mode(state, websocket_send)
        
        if mode == AgentMode.FAST:
            return await self._run_fast_mode(state, websocket_send)
        
        # Pass strategy to planning mode
        state.metadata["strategy"] = strategy
        return await self._run_planning_mode(state, websocket_send)

    async def _run_conversational(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Direct LLM response for simple conversational messages — no tools, no critic."""
        logger.info(f"[{state.session_id}] Orchestrator: conversational shortcut")
        
        messages = [
            {"role": "system", "content": "Ты — Archimedes, дружелюбный и профессиональный AI-ассистент. Отвечай на русском языке. Будь кратким и приветливым."},
            {"role": "user", "content": state.task_description}
        ]
        
        try:
            response = await self.router.generate(messages=messages, task_hint="think")
            result_text = response.get("text", "Привет! Чем могу помочь?")
            
            state.results.append({"step": 0, "output": result_text})
            return await self._get_final_response(state, websocket_send)
        except Exception as e:
            logger.error(f"Conversational response failed: {e}")
            fallback = "Привет! Я Archimedes — ваш AI-ассистент. Чем могу помочь?"
            state.results.append({"step": 0, "output": fallback})
            return await self._get_final_response(state, websocket_send)

    async def _run_fast_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering FAST mode")
        state = await self.executor.process(state, websocket_send)
        return await self._get_final_response(state, websocket_send)

    async def _run_planning_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering PLANNING mode")
        
        strategy = state.metadata.get("strategy", "swarm_code")
        
        # 1. PLAN
        state = await self.planner.process(state, websocket_send)
        if not state.current_plan:
             return {"success": False, "error": "Planning failed and fallback failed."}
        
        # 2. EXECUTE & CRITIQUE LOOP
        # Flatten subtasks for easier iteration
        all_subtasks = []
        for phase in state.current_plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                all_subtasks.append(subtask)
        
        # Section 2C: Parallel subtask execution for independent phases
        strategy_type = state.current_plan.get("strategy", "sequential")
        
        if strategy_type == "parallel" and len(all_subtasks) > 1:
            # Run all subtasks in parallel
            tasks = []
            for i, subtask in enumerate(all_subtasks):
                state_copy = OrchestrationState(
                    session_id=state.session_id,
                    task_description=subtask.get("description", ""),
                    mode=state.mode,
                    task_hint=state.task_hint,
                    current_plan=state.current_plan
                )
                state_copy.history = list(state.history)
                tasks.append(
                    self.executor.process(state_copy, websocket_send)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    state.results.append({
                        "step": i, "output": f"Error: {result}"
                    })
                else:
                    state.results.extend(result.results)
        else:
            # Sequential execution with strategy-aware dispatch
            for i, subtask in enumerate(all_subtasks):
                state.current_step_index = i
                
                # Reset per-subtask state to prevent cross-contamination
                state.reset_for_subtask()
                
                # Subtask loop (includes critic retries)
                while True:
                    current_target = subtask.get("description", state.task_description)
                    
                    # Strategy-aware dispatch: use swarm for matching strategies
                    agent_override = STRATEGY_AGENTS.get(strategy)
                    if strategy == "mcts":
                        if websocket_send:
                            await websocket_send({"type": "info", "content": "🔍 Запуск MCTS: Поиск оптимального решения через ветвление..."})
                            
                        # Context from history and task
                        context_str = state.task_description
                        try:
                            context_str += "\n" + "\n".join([msg["content"] for msg in state.history if msg["role"] == "user"])
                        except Exception:
                            pass
                            
                        mcts_result = await self.mcts_manager.run_mcts(
                            task=current_target,
                            context=context_str,
                            model_router=self.router,
                            executor_agent=self.executor,
                            state=state
                        )
                        state.results.append({
                            "step": i,
                            "output": f"MCTS Result:\n{mcts_result}"
                        })
                        state.metadata["critic_verdict"] = "PASS"
                    elif agent_override:
                        # Use swarm with strategy-specific agents
                        swarm_result = await self.swarm.run(
                            task=current_target,
                            task_hint=state.task_hint,
                            agent_roles_override=agent_override,
                            session_id=state.session_id,
                            websocket_send=websocket_send
                        )
                        state.results.append({
                            "step": i,
                            "output": swarm_result
                        })
                        
                        # Ensure critic has something to review
                        state = await self.critic.process(state, websocket_send)
                        
                        # Safety: If critic didn't set verdict, default to RETRY
                        # (not PASS — we don't want broken outputs to slip through)
                        if not state.metadata.get("critic_verdict"):
                            if state.current_retry_count >= state.critic_retry_limit:
                                state.metadata["critic_verdict"] = "LIMIT_REACHED"
                            else:
                                state.metadata["critic_verdict"] = "RETRY"
                                state.current_retry_count += 1
                    else:
                        state = await self.executor.process(state, websocket_send)
                        state = await self.critic.process(state, websocket_send)
                        
                        # Same safety guard for non-swarm path
                        if not state.metadata.get("critic_verdict"):
                            if state.current_retry_count >= state.critic_retry_limit:
                                state.metadata["critic_verdict"] = "LIMIT_REACHED"
                            else:
                                state.metadata["critic_verdict"] = "RETRY"
                                state.current_retry_count += 1
                    
                    verdict = state.metadata.get("critic_verdict")
                    
                    if verdict in ("PASS", "ERROR_BYPASS"):
                        # Subtask successful or best effort reached
                        break
                    elif verdict == "LIMIT_REACHED":
                        # Sprint 2.1: Recursive Self-Correction (Rescue Pass)
                        if not state.metadata.get("rescue_attempted", False):
                            logger.info(f"[{state.session_id}] Triggering Recursive Self-Correction Rescue Pass.")
                            state.metadata["rescue_attempted"] = True
                            
                            issues = state.metadata.get("critic_issues", [])
                            issues_text = "\n".join(issues)
                            
                            rescue_prompt = (
                                "SYSTEM CRITICAL: You have reached the maximum retry limit for this task. "
                                "The Quality Critic still rejects your output for the following reasons:\n"
                                f"{issues_text}\n\n"
                                "RECURSIVE SELF-CORRECTION PROTOCOL INITIATED:\n"
                                "1. You MUST use a search tool (like Exa/Tavily) to research these specific errors/issues.\n"
                                "2. Analyze the search results to find a definitive fix.\n"
                                "3. Apply the fix and provide your final corrected output.\n"
                                "Failure is not an option. Find the solution."
                            )
                            state.add_message("user", rescue_prompt)
                            # Reset retry count for one final attempt cycle
                            state.current_retry_count = 0
                            continue
                        else:
                            # Rescue already attempted and failed
                            logger.warning(f"[{state.session_id}] Rescue pass failed. Moving on.")
                            break
                    elif verdict == "RETRY":
                        # Continue loop to re-execute with critic feedback
                        continue
                    else:
                        # Unexpected state — safety break
                        logger.warning(
                            f"Unexpected critic verdict: {verdict}. Breaking loop."
                        )
                        break
                    
        return await self._get_final_response(state, websocket_send)

    async def _get_final_response(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Synthesize final output from results."""
        if not state.results:
            return {"success": False, "error": "No results generated."}
        
        # Fast mode: Just return the last result
        if state.mode == AgentMode.FAST or len(state.results) == 1:
            final_output = state.results[-1].get("output", "Done.")
        else:
            # Planning mode: Synthesize all steps into a cohesive response
            if websocket_send:
                await websocket_send({"type": "info", "content": "Синтезирую итоговый ответ..."})
            
            summary_prompt = "На основе результатов всех выполненных подзадач сформируй итоговый ответ пользователю на его изначальный запрос.\n\n"
            summary_prompt += f"ИЗНАЧАЛЬНЫЙ ЗАПРОС: {state.task_description}\n\n"
            for res in state.results:
                summary_prompt += f"Шаг {res.get('step')}: {res.get('output')}\n"
            
            try:
                response = await self.router.generate(
                    messages=[{"role": "user", "content": summary_prompt}],
                    task_hint="think"
                )
                final_output = response.get("text", state.results[-1].get("output", "Done."))
            except Exception as e:
                logger.error(f"Failed to synthesize final response: {e}")
                final_output = state.results[-1].get("output", "Done.")

        return {
            "success": True,
            "output": final_output,
            "history": state.history,
            "plan": state.current_plan,
            "mode": state.mode.value
        }
