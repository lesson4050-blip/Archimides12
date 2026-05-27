import logging
import re
import os
import asyncio
from typing import Optional, Callable, Dict, Any, List, Tuple
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.agent.orchestration.agents.planner_agent import PlannerAgent
from backend.agent.orchestration.agents.executor_agent import ExecutorAgent
from backend.agent.orchestration.agents.critic_agent import CriticAgent
from backend.agent.orchestration.agents.supervisor_agent import SupervisorAgent
from backend.agent.orchestration.agents.verification_agent import VerificationAgent
from backend.agent.orchestration.mcts import MCTSManager
from backend.models.model_router import ModelRouter, get_model_router
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager
from backend.agent.skill_library import SkillLibrary
from backend.telemetry import agent_span
from backend.agent.transparency.audit_trail import audit_manager, TaskAuditTrail

logger = logging.getLogger(__name__)

_PARALLEL_SEMAPHORE: Optional[asyncio.Semaphore] = None

def get_parallel_semaphore() -> asyncio.Semaphore:
    global _PARALLEL_SEMAPHORE
    if _PARALLEL_SEMAPHORE is None:
        _PARALLEL_SEMAPHORE = asyncio.Semaphore(4)
    return _PARALLEL_SEMAPHORE

_SENSITIVE_ENV_PREFIXES = (
    "DATABASE_", "DB_", "REDIS_", "SECRET_", "JWT_", "STRIPE_",
    "AWS_SECRET", "GITHUB_TOKEN", "PRIVATE_KEY", "SMTP_PASS",
)

def _run_mcts_subprocess(task: str, context: str) -> str:
    """Runs MCTS in a separate process to avoid blocking the event loop.
    
    SECURITY NOTE: This function executes inside a ProcessPoolExecutor worker.
    On Unix (fork), the child inherits env but is isolated. On Windows (spawn),
    a fresh process is created. In both cases, we do NOT mutate os.environ
    in the parent — that was a critical bug that stripped API keys globally.
    MCTS does not need database/auth secrets, so no sanitization is required.
    """
    import asyncio
    import os
    from backend.agent.orchestration.mcts import MCTSManager
    
    # Log if sensitive vars are present (diagnostic only — do NOT delete them
    # from os.environ, as that would affect the parent process on Windows).
    _leaked = [k for k in os.environ if any(k.upper().startswith(p) for p in _SENSITIVE_ENV_PREFIXES)]
    if _leaked:
        import logging
        logging.getLogger(__name__).debug(
            f"MCTS worker has {len(_leaked)} sensitive env vars inherited (process-isolated, safe)"
        )
    
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
    # Personal statements & memory requests
    r"\bmy\s+name\s+is\b",
    r"\bremember\s+(this|that|me|my)\b",
    r"\bзапомни\b",
    r"\bменя\s+зовут\b",
]

# Short personal recall patterns — these ARE questions but trivially conversational
_MEMORY_RECALL = re.compile(
    r"^(what('?s|\s+is)\s+my\s+name|как\s+меня\s+зовут)",
    re.IGNORECASE
)

def is_conversational(text: str) -> bool:
    """Check if the task is a simple conversational message (greeting, etc.).
    
    IMPORTANT: This must NOT match information-seeking questions.
    "What is Python?" is a QUESTION, not a greeting.
    Only explicit greetings/farewells/meta-questions should match.
    """
    cleaned = text.strip().lower()
    
    # Short personal recall questions are conversational
    if _MEMORY_RECALL.search(cleaned):
        return True
    
    # Never match if the message contains a question word — it's a real question
    question_signals = re.compile(
        r'\b(what|who|when|where|how|why|which|find|search|explain|tell me|show me|'
        r'что\b|кто\b|когда|где\b|как\b|почему|какой|какая|какие|найди|покажи|'
        r'расскажи|объясни|сколько|зачем)\b', re.IGNORECASE
    )
    # Exception: "что ты умеешь" / "кто ты" are meta-questions (handled by patterns)
    meta_questions = re.compile(
        r'(что\s+ты\s+(умеешь|такое|можешь)|кто\s+ты|'
        r'what can you do|who are you|what are you)', re.IGNORECASE
    )
    if question_signals.search(cleaned) and not meta_questions.search(cleaned):
        return False
    
    # Check explicit greeting/farewell patterns
    for pattern in CONVERSATIONAL_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
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
    (r"(research|find|search|analyze|compare|summarize|report|study|найди|поищи|найти|исследуй|новости|анализ)",
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


async def classify_task(text: str, router: Optional[Any] = None) -> Tuple[str, str]:
    """
    Returns (complexity, strategy) using multi-signal classification.
    
    Signal 1: Regex pattern match (fast path)
    Signal 2: Heuristic-based scoring
    Signal 3: LLM classification (slow but accurate fallback)
    """
    SEARCH_DIRECT = re.compile(
        r'\b(расскажи|what is|who is|покажи|что такое|почему|разница|explain|why|найди|найти|поищи|новости|news|find|search)\b',
        re.IGNORECASE
    )
    if SEARCH_DIRECT.search(text) and not any(w in text.lower() for w in ['код', 'code', 'fix', 'bug', 'implement', 'error', 'errors', 'issue', 'issues', 'test', 'tests', 'problem', 'problems', 'ошиб', 'баг']):
        return "simple", "direct"

    text_lower = text.lower().strip()
    
    # Signal 1: Check routing rules first — even for short inputs
    # Short tasks like "fix the bug" or "run tests" MUST hit routing rules
    # before falling back to "direct" (conversational without tools).
    for pattern, complexity, strategy in ROUTING_RULES:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return complexity, strategy
    
    # Signal 2: Heuristic scoring
    signals = {
        "has_code_markers": bool(re.search(r'[{}\[\]();=]|```|def |class |import |function ', text)),
        "has_tool_keywords": bool(re.search(r'(файл|file|запуст|run|выполн|exec|установ|install)', text_lower)),
        "has_multiple_steps": bool(re.search(r'(\d+[\.\)]\s|\bа также\b|\bи потом\b|\bthen\b)', text_lower)),
        "is_long": len(text_lower) > 200,
    }
    
    score = signals["has_code_markers"]*3 + signals["has_tool_keywords"]*2 + signals["has_multiple_steps"]*3
    if score >= 5: return "complex", "swarm_code"

    # Signal 3: LLM Classification (The "Brain")
    if router:
        # Emit a status update if this might take a while
        try:
             import asyncio
             # We can't easily emit to event_bus from here without passing it, 
             # so we'll just rely on the existing logging for now.
        except: pass
        try:
            prompt = f"""Classify this AI Agent task: "{text[:500]}"
Available strategies: swarm_code (multi-file coding), swarm_research (web search/analysis), codeact (single file fix), direct (chat/greeting), single (simple script).
Return ONLY: complexity,strategy (e.g. complex,swarm_code)"""
            response = await router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="quick"
            )
            raw = response.get("text", "").strip().lower()
            if "," in raw:
                comp, strat = raw.split(",", 1)
                return comp.strip(), strat.strip()
        except Exception:
            pass

    return "medium", "single"






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
                 context_manager: ContextManager,
                 session_id: str = "default"):
        from backend.agent.shared_blackboard import SharedBlackboard
        from backend.config import settings
        self.blackboard = SharedBlackboard(session_id=session_id, redis_url=settings.REDIS_URL)
        self.router = router
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.planner = PlannerAgent(router)
        self.executor = ExecutorAgent(router, tool_registry, context_manager, self.blackboard, event_bus=None, security_gate=None)  # Updated below
        self.critic = CriticAgent(router, tool_registry=tool_registry)
        self.supervisor = SupervisorAgent(router)
        self.verifier = VerificationAgent(router)
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

        self.event_bus = EventBus.get_instance(session_id)
        self.handoff = HandoffProtocol()
        self.security_gate = SecurityGate()
        self.cascade = CascadingRouter(router)

        # Wire production modules into executor (created above)
        self.executor.event_bus = self.event_bus
        self.executor.security_gate = self.security_gate
        
        self._session_llm_call_count: Dict[str, int] = {}
        self.MAX_LLM_CALLS_PER_SESSION = int(
            os.environ.get("MAX_LLM_CALLS_PER_SESSION", "200")
        )

    def _check_budget(self, session_id: str) -> bool:
        """Returns False if session has exceeded LLM call budget."""
        count = self._session_llm_call_count.get(session_id, 0)
        if count >= self.MAX_LLM_CALLS_PER_SESSION:
            logger.error(
                f"[{session_id}] Budget cap hit: {count} LLM calls >= "
                f"{self.MAX_LLM_CALLS_PER_SESSION} limit"
            )
            return False
        self._session_llm_call_count[session_id] = count + 1
        return True


    async def run_task(self, 
                       task_description: str, 
                       mode: AgentMode = AgentMode.PLANNING,
                       session_id: str = "default",
                       websocket_send: Optional[Callable] = None,
                       task_hint: str = "default",
                       stream: bool = False,
                       memory_message: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        TIMEOUT = int(os.environ.get("AGENT_TASK_TIMEOUT", "900"))
        import time
        from backend.metrics import agent_task_duration, agent_timeouts_total
        start = time.time()
        strategy = "unknown"
        try:
            result = await asyncio.wait_for(
                self._run_task_internal(
                    task_description, mode, session_id,
                    websocket_send, task_hint, stream, memory_message
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
                    "type": "agent_error",
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
                       stream: bool = False,
                       memory_message: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        
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

        import uuid
        trail_id = f"{session_id}-{str(uuid.uuid4())[:8]}"
        trail = audit_manager.start_trail(trail_id, task_description, session_id)
        state.metadata["audit_trail"] = trail
        state.metadata["audit_trail_id"] = trail_id

        # Inject mcp_client into state metadata for executor access
        state.metadata["mcp_client"] = getattr(self, '_mcp_client_ref', None)
        
        # Add initial greeting/task to history
        state.add_message("user", task_description)
        
        # If memory message provided, prepend to history
        if memory_message:
            state.add_message(memory_message["role"], memory_message["content"])

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
                result = await self._run_conversational(state, websocket_send)
                audit_data = audit_manager.complete_trail(trail_id)
                if audit_data and websocket_send:
                    await websocket_send({
                        "type": "audit_trail",
                        "task_id": trail_id,
                        "summary": {
                            "duration": audit_data["total_duration_seconds"],
                            "events": audit_data["event_count"],
                            "strategy": "conversational",
                        }
                    })
                result["audit_trail_id"] = trail_id
                return result
            
            # Semantic task routing
            complexity, strategy = await classify_task(task_description, self.router)
            state.metadata["complexity"] = complexity
            state.metadata["strategy"] = strategy

            trail.record_routing(
                chosen_strategy=strategy,
                chosen_complexity=complexity,
                alternatives_considered=["direct", "swarm_code", "swarm_research", "codeact"],
                reason=f"Pattern match or LLM classification"
            )
            
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
                    if strategy == "direct":
                        logger.info(f"[{session_id}] Simple direct task → conversational mode")
                        result = await self._run_conversational(state, websocket_send)
                    else:
                        logger.info(f"[{session_id}] Simple task → fast mode (strategy: {strategy})")
                        result = await self._run_fast_mode(state, websocket_send)
                elif mode == AgentMode.FAST or strategy == "single":
                    logger.info(f"[{session_id}] Strategy '{strategy}' matches fast execution.")
                    result = await self._run_fast_mode(state, websocket_send)
                else:
                    # Pass strategy to planning mode
                    state.metadata["strategy"] = strategy
                    result = await self._run_planning_mode(state, websocket_send)

                audit_data = audit_manager.complete_trail(trail_id)
                if audit_data and websocket_send:
                    await websocket_send({
                        "type": "audit_trail",
                        "task_id": trail_id,
                        "summary": {
                            "duration": audit_data["total_duration_seconds"],
                            "events": audit_data["event_count"],
                            "strategy": strategy,
                        }
                    })
                # Store full trail in result
                result["audit_trail_id"] = trail_id
                
                return result
        finally:
            # Guaranteed cleanup: remove consumer from EventBus on ALL exit paths
            if websocket_send:
                self.event_bus.remove_consumer(websocket_send)

    async def _run_conversational(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        """Direct LLM response for simple conversational messages — no tools, no critic.
        
        FIX-3: Now uses CoT for complex reasoning tasks that arrive via this path.
        """
        logger.info(f"[{state.session_id}] Orchestrator: conversational shortcut")
        from backend.agent.intelligence.cot_engine import inject_cot, extract_cot_answer
        
        system_prompt = (
            "You are Archimedes, a professional AI assistant. "
            "Respond in the same language the user uses. "
            "Be concise and friendly. "
            "If conversation history is provided, use it to answer personal questions."
        )
        
        # Proactive search for information questions
        search_context = ""
        if not _MEMORY_RECALL.search(state.task_description):
            search_context = await self._maybe_search_for_context(state.task_description) or ""
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Inject dynamic search results as a separate user message (preserves KV-cache prefix)
        if search_context:
            messages.append({
                "role": "user",
                "content": (
                    "[RELEVANT SEARCH RESULTS — use these to answer accurately]\n"
                    f"{search_context}\n"
                    "[END SEARCH RESULTS]"
                )
            })
        
        # Include prior conversation turns
        try:
            prior = self.context_manager.get_messages()
            for msg in prior:
                if msg.get("role") in ("user", "assistant") and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})
        except Exception:
            pass
        
        messages.append({"role": "user", "content": state.task_description})

        # FIX-3: Detect if reasoning is needed
        task_lower = state.task_description.lower()
        needs_reasoning = any(w in task_lower for w in [
            'why', 'explain', 'analyze', 'compare', 'difference',
            'почему', 'объясни', 'сравни', 'проанализируй', 'разница'
        ])
        
        try:
            if needs_reasoning:
                await self.event_bus.emit_thought("Analyzing request with deep reasoning...", agent="orchestrator")
                messages = inject_cot(messages, task=state.task_description)
                
                if websocket_send:
                    async def _on_token(token):
                        await websocket_send({"type": "token", "content": token})
                    
                    response = await self.cascade.generate_stream(
                        messages=messages, 
                        task_hint="think",
                        on_token=_on_token
                    )
                else:
                    response = await self.cascade.generate(messages=messages, task_hint="think")
                
                raw_text = response.get("text", "")
                cot_data = extract_cot_answer(raw_text)
                result_text = cot_data["answer"]
                
                # Emit the thinking process if we have it
                if cot_data["thinking"]:
                    await self.event_bus.emit_thought(cot_data["thinking"], agent="reasoner")
            else:
                if websocket_send:
                    async def _on_token(token):
                        await websocket_send({"type": "token", "content": token})
                    
                    response = await self.cascade.generate_stream(
                        messages=messages, 
                        task_hint="quick",
                        on_token=_on_token
                    )
                else:
                    response = await self.cascade.generate(messages=messages, task_hint="quick")
                
                result_text = response.get("text", "Привет! Чем могу помочь?")

            state.results.append({"step": 0, "output": result_text})
            return await self._get_final_response(state, websocket_send)
        except Exception as e:
            logger.error(f"Conversational response failed: {e}")
            # Dynamic fallback based on input language
            is_russian = any(c in 'йцукенгшщзхъфывапролджэячсмитьбю' for c in state.task_description.lower())
            fallback = "Привет! Я Archimedes — твой AI-ассистент. Чем могу помочь?" if is_russian else "Hello! I am Archimedes, your AI assistant. How can I help you?"
            state.results.append({"step": 0, "output": fallback})
            return await self._get_final_response(state, websocket_send)

    async def _run_fast_mode(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"[{state.session_id}] Orchestrator entering FAST mode")
        state = await self.executor.process(state, websocket_send)
        return await self._get_final_response(state, websocket_send)

    # ── FIX-2: Proactive search for information questions ──
    
    _SEARCH_TRIGGER = re.compile(
        r'\b(what|who|when|where|how|why|which|find|search|look up|'
        r'tell me about|explain|latest|current|today|news|price|weather|'
        r'что|кто|когда|где|как|почему|найди|расскажи|объясни|'
        r'последн|сейчас|новост|цена|погода|курс|сколько)\b', re.IGNORECASE
    )

    async def _maybe_search_for_context(self, query: str) -> str:
        """Proactively search if the query looks like an information question.
        
        Returns search context string or empty string if not applicable.
        Guards against empty ToolRegistry — logs warning if search tool is missing.
        """
        if not self._SEARCH_TRIGGER.search(query):
            return ""
        
        # GUARD: Verify search tool is actually registered (not silent fail)
        if "search" not in self.tool_registry.tools:
            logger.warning(
                "TOOL REGISTRY GUARD: 'search' tool not registered. "
                "Proactive search skipped. This may indicate a ToolInitializer failure."
            )
            return ""
        
        try:
            search_result = await self.tool_registry.execute_tool(
                "search", {"query": query, "max_results": 3}
            )
            if search_result.get("success"):
                output = search_result.get("output", "")
                if output and len(str(output)) > 20:
                    logger.info(f"Proactive search returned {len(str(output))} chars")
                    return str(output)[:2000]  # Cap context size
        except Exception as e:
            logger.debug(f"Proactive search skipped: {e}")
        
        return ""

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

        complexity = state.metadata.get("complexity", "complex")
        strategy = state.metadata.get("strategy", "swarm_code")
        task_lower = state.task_description.lower()

        # Only show HITL for genuinely complex tasks
        should_show_hitl = (
            strategy in ('swarm_code', 'codeact') and  # Only for coding
            complexity == 'complex' and
            not any(kw in task_lower for kw in [
                'найди', 'поищи', 'search', 'find', 'what is', 'tell me',
                'расскажи', 'новости', 'news'
            ])
        )
        
        # plan approval gate loop
        while os.environ.get("TESTING") != "1" and websocket_send and should_show_hitl:
            from backend.websocket.handler import manager as ws_manager
            phases_text = []
            for p_idx, phase in enumerate(state.current_plan.get("phases", [])):
                phases_text.append(f"🟢 **Фаза {p_idx+1}: {phase.get('name', 'Без названия')}**")
                for s_idx, subtask in enumerate(phase.get("subtasks", [])):
                    phases_text.append(f"  - Шаг {s_idx+1}: {subtask.get('description')}")
            
            plan_prompt = (
                "📋 **Сформирован пошаговый план действий:**\n\n"
                + "\n".join(phases_text) + "\n\n"
                "Отправьте **'yes'** (или просто отправьте пустое сообщение/Enter), чтобы утвердить этот план.\n"
                "Если у вас есть замечания, напишите их ниже для корректировки:"
            )
            
            user_response = await ws_manager.get_user_approval(state.session_id, plan_prompt)
            user_response_clean = user_response.strip().lower() if user_response else ""
            
            if user_response_clean in ("", "yes", "да", "одобрить", "одобрено", "окей", "ок"):
                await self.event_bus.emit_thought("Plan approved by user. Starting execution...", agent="orchestrator")
                break
            else:
                # Replan
                await self.event_bus.emit_thought(f"User requested changes to the plan: {user_response}. Replanning...", agent="orchestrator")
                state.add_message("user", f"Пожалуйста, скорректируй план с учетом замечаний: {user_response}")
                state = await self.planner.process(state, websocket_send)
                if not state.current_plan:
                    return {"success": False, "error": "Planning failed during replan."}

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
                
                # Subtask HITL approval gate
                if os.environ.get("TESTING") != "1" and websocket_send and should_show_hitl:
                    from backend.websocket.handler import manager as ws_manager
                    subtask_prompt = (
                        f"🚀 **Готов приступить к шагу {i+1} из {len(all_subtasks)}:**\n"
                        f"Описание: *{subtask.get('description')}*\n\n"
                        "Отправьте **'yes'** (или Enter) для запуска шага, либо напишите свои корректировки:"
                    )
                    user_response = await ws_manager.get_user_approval(state.session_id, subtask_prompt)
                    user_response_clean = user_response.strip().lower() if user_response else ""
                    if user_response_clean not in ("", "yes", "да", "одобрить", "одобрено", "окей", "ок"):
                        # User provided feedback for the subtask
                        await self.event_bus.emit_thought(f"User adjusted step {i+1}: {user_response}", agent="orchestrator")
                        # Inject feedback into the subtask description so the executor executes it with feedback!
                        subtask["description"] = f"{subtask['description']} (ВАЖНОЕ указание пользователя: {user_response})"

                # Circuit Breaker: hard cap to prevent infinite loops
                _MAIN_LOOP_LIMIT = 8      # Reduced from 15 to prevent long stuck loops
                _RESCUE_LOOP_LIMIT = 8    # Rescue pass gets its own budget
                _main_count = 0
                _rescue_count = 0
                _in_rescue = False
                
                current_target = subtask.get("description", state.task_description)
                
                async with agent_span("executor.subtask", state.session_id, subtask_index=i, target=current_target[:50]):
                    while True:
                        # FIX-1: Read strategy from state each iteration (prevents NameError)
                        strategy = state.metadata.get("strategy", "swarm_code")
                        
                        if not self._check_budget(state.session_id):
                            from backend.metrics import agent_circuit_breaker_total
                            agent_circuit_breaker_total.inc()
                            if websocket_send:
                                await websocket_send({
                                    "type": "agent_error",
                                    "content": "⚠️ Session budget limit reached. Task stopped to prevent runaway costs."
                                })
                            break
                        
                        if _in_rescue:
                            _rescue_count += 1
                            if _rescue_count > _RESCUE_LOOP_LIMIT:
                                logger.warning(f"[{state.session_id}] Rescue pass exhausted ({_RESCUE_LOOP_LIMIT} iters).")
                                break
                        else:
                            _main_count += 1
                            if _main_count > _MAIN_LOOP_LIMIT:
                                from backend.metrics import agent_circuit_breaker_total
                                agent_circuit_breaker_total.inc()
                                logger.warning(f"[{state.session_id}] Main circuit breaker tripped! >{_MAIN_LOOP_LIMIT} iterations.")
                                if websocket_send:
                                    await websocket_send({
                                        "type": "agent_error",
                                        "content": "⚠️ Maximum execution steps reached. The task might be too complex or the agent is stuck."
                                    })
                                break
                        
                        # Strategy-aware dispatch: use swarm for matching strategies
                        agent_override = STRATEGY_AGENTS.get(strategy)
                        if strategy == 'swarm_code':
                            agent_override = ['coder']
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
                            if strategy != 'swarm_code':
                                state = await self.critic.process(state, websocket_send)
                            else:
                                state.metadata["critic_verdict"] = "PASS"
                        
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
                                _in_rescue = True          # ← Switch to rescue counter
                                _rescue_count = 0          # ← Reset rescue counter
                                
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
                    
        # Run VerificationAgent on completed coding tasks
        changed_files = getattr(state, 'changed_files', None) or state.metadata.get("changed_files", [])
        if changed_files and strategy_type in ("swarm_code", "codeact"):
            try:
                from backend.agent.orchestration.agents.verification_agent import VerificationAgent
                verifier = VerificationAgent(router=self.router)
                state = await verifier.process(state, websocket_send)
                
                verification = state.metadata.get("verification_report", {})
                if not verification.get("passed", True):
                    logger.warning(
                        f"Verification failed: {verification.get('summary')}"
                    )
                    # Emit to UI
                    if websocket_send:
                        await websocket_send({
                            "type": "verification_report",
                            "passed": False,
                            "summary": verification.get("summary"),
                            "checks": verification.get("checks", [])
                        })
            except Exception as e:
                logger.debug(f"Post-task verification skipped: {e}")

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
        
        # Episodic Memory Storage
        try:
            from backend.memory.memory_router import MemoryRouter
            mem_router = MemoryRouter(
                user_id=state.metadata.get("user_id", "default"),
                session_id=state.session_id
            )
            # Store the task and the final synthesized result
            await mem_router.store(
                task=state.task_description,
                result=final_output,
                metadata={
                    "strategy": state.metadata.get("strategy", "unknown"),
                    "mode": state.mode.value
                }
            )
            logger.info(f"[{state.session_id}] Orchestrator: Result stored in episodic memory")
        except Exception as e:
            logger.warning(f"Failed to store result in memory: {e}")

        return {"success": True, "output": final_output,
                "history": state.history, "plan": state.current_plan,
                "mode": state.mode.value}
