import logging
import re
import os
import asyncio
from typing import Optional, Callable, Dict, Any, List, Tuple
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.agent.orchestration.agents.planner_agent import PlannerAgent
from backend.agent.orchestration.agents.executor_agent import ExecutorAgent
from backend.agent.orchestration.agents.critic_agent import CriticAgent
from backend.agent.orchestration.agents.verification_agent import VerificationAgent
from backend.agent.orchestration.mcts import MCTSManager
from backend.models.model_router import ModelRouter, get_model_router
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager
from backend.agent.skill_library import SkillLibrary
from backend.telemetry import agent_span

logger = logging.getLogger(__name__)

_PARALLEL_SEMAPHORE: Optional[asyncio.Semaphore] = None

def get_parallel_semaphore() -> asyncio.Semaphore:
    global _PARALLEL_SEMAPHORE
    if _PARALLEL_SEMAPHORE is None:
        _PARALLEL_SEMAPHORE = asyncio.Semaphore(4)
    return _PARALLEL_SEMAPHORE

def _run_mcts_subprocess(task: str, context: str) -> str:
    """Runs MCTS in a separate process to avoid blocking the event loop."""
    import asyncio
    from backend.agent.orchestration.mcts import MCTSManager
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        mgr = MCTSManager(workspace_dir=".")
        # MCTSManager needs a simplified interface here — just task+context
        if hasattr(mgr, 'run_simple'):
            result = loop.run_until_complete(mgr.run_simple(task, context))
        else:
            router = get_model_router()
            result = loop.run_until_complete(mgr.run_mcts(task, context, router, None, None))
        return result or ""
    finally:
        loop.close()


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
    # Hydra Swarm routes
    (r"(hydra.*swarm|system.*refactor|full.*stack.*feature)",
     "complex", "hydra_swarm"),
    # Omega CodeAct routes
    (r"(omega.*codeact|100.*iterations|extreme.*fix|deep.*debug|swe.*bench.*hard)",
     "complex", "omega_codeact"),
    # CodeAct routes — precise single-file bug fixes
    (r"(fix the bug|patch|apply.*fix|reproduce.*error|failing test|"
     r"исправь.*ошибку|примени.*патч)",
     "complex", "codeact"),
    (r"(swe.?bench|github.*issue|pull request|bugfix|bug fix)",
     "complex", "codeact"),
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
    (r"(codeact|autonomous code|multi-file refactor)",
     "complex", "codeact"),
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
        # Ambiguous — will be LLM-classified by orchestrator if needed
        return "medium", "single"


async def classify_task_with_llm(
    text: str,
    router: ModelRouter,
    fallback_result: tuple = None
) -> tuple:
    """
    LLM-based task classification for ambiguous tasks.
    Falls back to regex result if LLM fails.
    Only called for medium-length tasks that regex can't clearly route.
    """
    prompt = (
        "Classify this task into one routing category.\n"
        f"Task: {text[:300]}\n\n"
        "Categories:\n"
        "- hydra_swarm: system refactoring, complex full-stack features\n"
        "- omega_codeact: extreme fix, SWE-bench hard, 100 iterations\n"
        "- codeact: fix a bug, apply a patch, SWE-bench style fix\n"
        "- swarm_code: write new code, build a feature, implement API\n"
        "- swarm_research: research, analyze, compare, summarize\n"
        "- mcts: explore multiple solutions, needs creative alternatives\n"
        "- single: simple translation, calculation, single-step task\n"
        "- direct: greeting, trivial question\n\n"
        "Reply with ONLY the category name. Nothing else."
    )
    try:
        response = await router.generate(
            messages=[{"role": "user", "content": prompt}],
            task_hint="quick"
        )
        category = response.get("text", "").strip().lower()
        valid = {"hydra_swarm", "omega_codeact", "codeact", "swarm_code", "swarm_research",
                 "mcts", "single", "direct"}
        if category in valid:
            complexity = "complex" if category not in ("single", "direct") else "simple"
            return complexity, category
    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        pass
    return fallback_result or ("medium", "single")


# Strategy to swarm agent types mapping
STRATEGY_AGENTS = {
    "swarm_code": ["coder", "critic", "tester"],
    "swarm_research": ["researcher", "critic"],
    "swarm_architect": ["architect", "coder", "critic"],
    "single": None,
    "single_slides": None,
    "direct": None,
    "mcts": None,
    "codeact": None,
    "omega_codeact": None,
    "hydra_swarm": None,
}


class AgentOrchestrator:
    """
    Coordinates the multi-agent flow: Planner -> Executor -> Critic.
    
    Production modules integrated:
      - EventBus:         Real-time streaming of all agent thoughts/actions
      - CascadingRouter:  Adaptive model selection (cost/latency optimization)
      - SecurityGate:     5-layer defense-in-depth for command execution
      - StateCheckpoint:  Crash-resilient state persistence (WAL pattern)
      - HandoffProtocol:  Zero-loss context transfer between agents
    """
    def __init__(self, 
                 router: ModelRouter, 
                 tool_registry: ToolRegistry, 
                 context_manager: ContextManager):
        from backend.agent.shared_blackboard import SharedBlackboard
        self.blackboard = SharedBlackboard()
        self.router = router
        self.tool_registry = tool_registry
        self.planner = PlannerAgent(router)
        self.executor = ExecutorAgent(router, tool_registry, context_manager, self.blackboard, event_bus=None, security_gate=None)  # Updated below
        self.critic = CriticAgent(router)
        from backend.agent.orchestration.swarm import MicroAgentSwarm
        self.swarm = MicroAgentSwarm(router, tool_registry=tool_registry)
        self.mcts_manager = MCTSManager(workspace_dir=".")
        self.skill_library = SkillLibrary()
        self._parallel_result_bus: Dict[str, Any] = {}
        self._mcp_client_ref = None  # Set by core.py after init
        
        import concurrent.futures
        self._process_executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)

        # ── Production Module Integration ──
        from backend.agent.orchestration.event_bus import EventBus
        from backend.agent.orchestration.context_protocol import HandoffProtocol
        from backend.agent.orchestration.state_checkpoint import StateCheckpoint
        from backend.models.cascading_router import CascadingRouter
        from backend.security.sandbox_hardening import SecurityGate

        self.event_bus = EventBus()
        self.handoff = HandoffProtocol()
        self.security_gate = SecurityGate()
        self.cascade = CascadingRouter(router)

        # Wire production modules into executor (created above)
        self.executor.event_bus = self.event_bus
        self.executor.security_gate = self.security_gate


    async def run_task(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None,
                       task_hint: str = "default",
                       stream: bool = False) -> Dict[str, Any]:
        TIMEOUT = int(os.environ.get("AGENT_TASK_TIMEOUT", "300"))
        import time
        from backend.metrics import agent_task_duration, agent_timeouts_total
        start = time.time()
        strategy = "unknown"
        try:
            result = await asyncio.wait_for(
                self._run_task_internal(
                    task_description, mode, session_id,
                    websocket_send, task_hint, stream
                ),
                timeout=TIMEOUT
            )
            if "strategy" in result:
                strategy = result["strategy"]
            
            # Record in Flywheel
            from backend.agent.flywheel import flywheel
            history = result.get("history", [])
            flywheel.record_session(session_id, task_description, result, history)
            
            # Store episodic memory
            if result.get("success"):
                try:
                    from backend.memory.memory_router import MemoryRouter
                    mem_router = MemoryRouter(user_id="default", session_id=session_id)
                    await mem_router.store(
                        task=task_description,
                        result=str(result.get("output", ""))[:300],
                        memory_type="episodic"
                    )
                except Exception as e:
                    logger.warning(f"Failed to store episodic memory: {e}")
            
            return result
        except asyncio.TimeoutError:
            agent_timeouts_total.inc()
            logger.error(f"[{session_id}] Task timed out after {TIMEOUT}s")
            if websocket_send:
                await websocket_send({
                    "type": "error",
                    "content": f"⏱️ Agent timed out after {TIMEOUT//60} minutes."
                })
            return {"success": False, "error": "timeout",
                    "output": "Task timed out. Please try a simpler request."}
        finally:
            duration = time.time() - start
            agent_task_duration.labels(strategy=strategy).observe(duration)
        
    async def _run_task_internal(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None,
                       task_hint: str = "default",
                       stream: bool = False) -> Dict[str, Any]:
        
        # ── Wire EventBus to WebSocket consumer ──
        self.event_bus.session_id = session_id
        if websocket_send:
            self.event_bus.add_consumer(websocket_send)

        # ── Create per-session checkpoint (crash-resilient) ──
        from backend.agent.orchestration.state_checkpoint import StateCheckpoint
        try:
            checkpoint = StateCheckpoint(session_id)
        except Exception as e:
            logger.warning(f"StateCheckpoint init failed: {e}. Using no-op checkpoint.")

            class _NoOpCheckpoint:
                async def save(self, *a, **kw): pass
                async def append_wal(self, *a, **kw): pass
                async def recover(self): return None

            checkpoint = _NoOpCheckpoint()

        # ── Create context envelope for zero-loss handoff ──
        envelope = self.handoff.create_envelope(
            user_request=task_description,
            session_id=session_id,
        )

        # Initialize state
        state = OrchestrationState(
            session_id=session_id,
            task_description=task_description,
            mode=mode,
            task_hint=task_hint,
            stream=stream,
        )

        # Inject mcp_client into state metadata for executor access
        state.metadata["mcp_client"] = getattr(self, '_mcp_client_ref', None)
        
        # Add initial greeting/task to history
        state.add_message("user", task_description)
        
        # Unified Memory Router integration
        try:
            from backend.memory.memory_router import MemoryRouter
            mem_router = MemoryRouter(
                user_id=state.metadata.get("user_id", "default"),
                session_id=session_id
            )
            context_str = await mem_router.get_context_string(task_description, max_tokens=2000)
            if context_str:
                state.add_message("system", f"Memory Context:\n{context_str}")
        except Exception as e:
            logger.warning(f"MemoryRouter context retrieval failed: {e}")

        # ── ALL return paths wrapped in try/finally for guaranteed consumer cleanup ──
        try:
            # EventBus: emit task start
            await self.event_bus.emit_thought(f"Task received: {task_description[:200]}", agent="orchestrator")
            
            # Inject Skill Library context if matching playbook exists
            skill_ctx = self.skill_library.get_context_prompt(task_description)
            if skill_ctx:
                state.add_message("system", skill_ctx)
                logger.info("SkillLibrary: injected matching playbook")
            
            # Shortcut: conversational messages get answered directly without planning/critic
            if is_conversational(task_description):
                logger.info(f"[{session_id}] Detected conversational message, using direct response")
                return await self._run_conversational(state, websocket_send)
            
            # Semantic task routing
            complexity, strategy = classify_task(task_description)
            
            # For medium-complexity ambiguous tasks, use LLM to refine routing
            # (Reserved for future A/B testing — not called in production)
            
            async with agent_span("orchestrator.task", session_id, strategy=strategy, mode=mode.value):
                # EventBus: emit routing decision
                await self.event_bus.emit_thought(
                    f"Route: complexity={complexity}, strategy={strategy}", agent="orchestrator"
                )

                # HandoffProtocol: record orchestrator's routing decision
                self.handoff.agent_handoff(envelope, "Orchestrator", notes={
                    "complexity": complexity, "strategy": strategy, "mode": mode.value,
                })

                # StateCheckpoint: save initial state
                try:
                    await checkpoint.save({
                        "task": task_description, "complexity": complexity,
                        "strategy": strategy, "phase": "routed",
                    })
                except Exception as e:
                    logger.warning(f"Checkpoint save failed (non-critical): {e}")

                if complexity == "simple":
                    logger.info(f"[{session_id}] Simple task → fast mode (strategy: {strategy})")
                    return await self._run_fast_mode(state, websocket_send)
                
                if mode == AgentMode.FAST or strategy == "single":
                    logger.info(f"[{session_id}] Strategy '{strategy}' matches fast execution.")
                    return await self._run_fast_mode(state, websocket_send)
                
                # Pass strategy to planning mode
                state.metadata["strategy"] = strategy
                return await self._run_planning_mode(state, websocket_send)
        finally:
            # Guaranteed cleanup: remove consumer from EventBus on ALL exit paths
            if websocket_send:
                self.event_bus.remove_consumer(websocket_send)

    async def _run_conversational(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Direct LLM response for simple conversational messages — no tools, no critic."""
        logger.info(f"[{state.session_id}] Orchestrator: conversational shortcut")
        
        messages = [
            {"role": "system", "content": "Ты — Archimedes, дружелюбный и профессиональный AI-ассистент. Respond in the same language the user used. Будь кратким и приветливым."},
            {"role": "user", "content": state.task_description}
        ]
        
        try:
            response = await self.cascade.generate(messages=messages, task_hint="quick")
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

    async def _run_planning_mode(self, state: OrchestrationState, websocket_send: Optional[Callable]) -> Dict[str, Any]:
        """Runs the planner agent to decompose the task and executes the plan."""
        from backend.metrics import agent_tasks_total
        strategy = state.metadata.get("strategy", "unknown")
        agent_tasks_total.labels(strategy=strategy, mode=state.mode.value).inc()
        
        # Determine strategy from metadata if present, otherwise default to "linear"
        strategy_type = state.metadata.get("strategy", "linear")
        logger.info(f"[{state.session_id}] Orchestrator running with strategy: {strategy_type}")
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
            
            async def _guarded(coro):
                async with get_parallel_semaphore():
                    return await coro

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
                # Inject mcp_client so parallel agents can use auto-tooling
                state_copy.metadata["mcp_client"] = state.metadata.get("mcp_client")
                state_copy.metadata["strategy"] = state.metadata.get("strategy", "swarm_code")
                tasks.append(_guarded(
                    self.executor.process(state_copy, websocket_send)
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Share successful results with subsequent agents via metadata
            successful_outputs = []
            for i, result in enumerate(results):
                if not isinstance(result, Exception) and result.results:
                    output = result.results[-1].get("output", "")
                    if output and len(output) > 10:
                        successful_outputs.append(f"Agent {i} result: {output[:500]}")
                    state.results.extend(result.results)
                elif isinstance(result, Exception):
                    state.results.append({
                        "step": i, "output": f"Error: {result}"
                    })

            # Store for potential follow-up sequential steps
            self._parallel_result_bus[state.session_id] = successful_outputs
        else:
            # Sequential execution with strategy-aware dispatch
            for i, subtask in enumerate(all_subtasks):
                state.current_step_index = i
                
                # Reset per-subtask state to prevent cross-contamination
                state.reset_for_subtask()
                
                # Subtask loop (includes critic retries)
                # Circuit Breaker: hard cap to prevent infinite loops
                _circuit_breaker_limit = 15
                _circuit_breaker_count = 0
                
                current_target = subtask.get("description", state.task_description)
                
                async with agent_span("executor.subtask", state.session_id, subtask_index=i, target=current_target[:50]):
                    while True:
                        _circuit_breaker_count += 1
                        if _circuit_breaker_count > _circuit_breaker_limit:
                            from backend.metrics import agent_circuit_breaker_total
                            agent_circuit_breaker_total.inc()
                            logger.warning(f"[{state.session_id}] Circuit breaker tripped! >15 iterations.")
                            if websocket_send:
                                await websocket_send({
                                    "type": "error",
                                    "content": "⚠️ Maximum execution steps reached. The task might be too complex or the agent is stuck."
                                })
                            break
                        
                        # Strategy-aware dispatch: use swarm for matching strategies
                        agent_override = STRATEGY_AGENTS.get(strategy)
                        if strategy == "mcts":
                            if websocket_send:
                                await websocket_send({"type": "info", "content": "🔍 Запуск MCTS: Поиск оптимального решения через ветвление..."})
                            
                            # Context from history and task
                            context_str = state.task_description
                            try:
                                context_str += "\n" + "\n".join([msg["content"] for msg in state.history if msg["role"] == "user"])
                            except (KeyError, TypeError) as e:
                                logger.debug(f"Failed to build MCTS context: {e}")
                                pass
                            
                            loop = asyncio.get_running_loop()
                            mcts_result = await loop.run_in_executor(
                                self._process_executor,
                                _run_mcts_subprocess,
                                current_target,
                                context_str
                            )
                            state.results.append({
                                "step": i,
                                "output": f"MCTS Result:\n{mcts_result}"
                            })
                            state.metadata["critic_verdict"] = "PASS"
                        elif strategy == "codeact":
                            from backend.agent.codeact_executor import CodeActExecutor
                            codeact = CodeActExecutor(self.router)
                            codeact_result = await codeact.execute(
                                task=current_target,
                                context=state.task_description,
                                session_id=state.session_id,
                                websocket_send=websocket_send,
                            )
                            state.results.append({
                                "step": i,
                                "output": codeact_result.get("output", ""),
                            })
                            state.metadata["critic_verdict"] = (
                                "PASS" if codeact_result.get("success") else "RETRY"
                            )
                        elif strategy == "omega_codeact":
                            from backend.agent.omega_codeact import OmegaCodeAct
                            omega = OmegaCodeAct(self.router)
                            omega_result = await omega.execute(
                                task=current_target,
                                context=state.task_description,
                                session_id=state.session_id,
                                websocket_send=websocket_send,
                            )
                            state.results.append({
                                "step": i,
                                "output": omega_result.get("output", ""),
                            })
                            state.metadata["critic_verdict"] = (
                                "PASS" if omega_result.get("success") else "RETRY"
                            )
                        elif strategy == "hydra_swarm":
                            from backend.agent.orchestration.hydra_swarm import HydraSwarm
                            hydra = HydraSwarm(self.router, self.tool_registry)
                            hydra_result = await hydra.run(
                                task=current_target,
                            )
                            state.results.append({
                                "step": i,
                                "output": str(hydra_result),
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
                    
        # Phase 4: Verification (read-only, runs tests)
        changed_files = getattr(state, 'changed_files', None) or state.metadata.get('changed_files', [])
        if changed_files:
            try:
                verifier = VerificationAgent(self.router)
                verification_result = await verifier.verify(changed_files, state.task_description)
                state.metadata["verification_report"] = verification_result.to_dict()
                if not verification_result.passed:
                    logger.warning(f"Verification failed: {verification_result.summary}")
            except Exception as e:
                logger.warning(f"Verification skipped: {e}")

        return await self._get_final_response(state, websocket_send)

    async def _get_final_response(self, state, websocket_send=None):
        if not state.results:
            return {"success": False, "error": "No results generated."}
        
        # Fast path: single result or fast mode — no synthesis needed
        if state.mode == AgentMode.FAST or len(state.results) == 1:
            final_output = state.results[-1].get("output", "Done.")
            return {"success": True, "output": final_output,
                    "history": state.history, "plan": state.current_plan,
                    "mode": state.mode.value}
        
        # Smart synthesis gate:
        # If the last result is long (>300 chars) and contains structured content,
        # it's likely already a complete answer — skip synthesis
        last_output = str(state.results[-1].get("output", ""))
        is_already_complete = (
            len(last_output) > 300 and
            # Contains code blocks, lists, or structured output
            any(marker in last_output for marker in
                ["```", "\n-", "\n1.", "##", "✅", "TASK_COMPLETE", "SUCCESS"])
        )
        
        if is_already_complete:
            logger.info("_get_final_response: skipping synthesis (last result is complete)")
            return {"success": True, "output": last_output,
                    "history": state.history, "plan": state.current_plan,
                    "mode": state.mode.value, "_synthesis_skipped": True}
        
        # Multi-step synthesis needed — use "default" hint, NOT "think"
        # "think" is the most expensive tier; synthesis doesn't need deep reasoning
        if websocket_send:
            await websocket_send({"type": "info", "content": "Synthesizing..."})
        
        # Build COMPRESSED summary (not full outputs — just last 200 chars each)
        summary_parts = [
            f"Original request: {state.task_description}\n\nResults summary:"
        ]
        for res in state.results:
            output = str(res.get("output", ""))
            # Take last 200 chars of each result (conclusion, not full content)
            summary_parts.append(f"Step {res.get('step')}: ...{output[-200:]}")
        
        summary_prompt = "\n".join(summary_parts)
        summary_prompt += (
            "\n\nSynthesize a final response. "
            "Respond in the SAME LANGUAGE as the original request. "
            "Be concise — the user saw intermediate results already."
        )
        
        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": summary_prompt}],
                task_hint="default"   # was "think" — saves ~60% cost on synthesis
            )
            final_output = response.get("text", last_output)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            final_output = last_output
        
        return {"success": True, "output": final_output,
                "history": state.history, "plan": state.current_plan,
                "mode": state.mode.value}
