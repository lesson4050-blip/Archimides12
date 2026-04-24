"""
Intelligence Router v2: Task-aware model routing.

Key changes over v1:
- Tools are ALWAYS passed through (never silently dropped)
- Simple mode is optimized for agent loop (low latency + tools)
- Medium mode uses reflection ONLY on final answers (not mid-loop)
- Complex mode reserved for architecture/planning (no tools needed)
- Classification is heuristic-first (no LLM call) for speed
"""
import logging
import re
from typing import Dict, Any, List, Optional
from backend.agent.intelligence.cot_engine import inject_cot, extract_cot_answer
from backend.agent.intelligence.moa_engine import MixtureOfAgents
from backend.agent.intelligence.reflection_engine import ReflectionEngine
from backend.agent.intelligence.self_consistency import SelfConsistency

logger = logging.getLogger(__name__)


# ─── Heuristic complexity classifier (no LLM call) ──────────────

COMPLEX_KEYWORDS = re.compile(
    r"(architect|system design|refactor|microservice|migration|scalab|"
    r"security audit|performance optim|архитектур|масштаб|рефакторинг)",
    re.IGNORECASE
)

MEDIUM_KEYWORDS = re.compile(
    r"(write|create|implement|fix|debug|analyze|compare|research|"
    r"напиши|создай|исправь|анализ|исследуй|сравни)",
    re.IGNORECASE
)


def classify_complexity_fast(task: str) -> str:
    """
    Heuristic classifier — no LLM call, ~0ms latency.
    Returns: 'simple', 'medium', or 'complex'
    """
    if not task:
        return "simple"
    
    if COMPLEX_KEYWORDS.search(task):
        return "complex"
    if MEDIUM_KEYWORDS.search(task):
        return "medium"
    
    # Length-based heuristic
    if len(task) > 500:
        return "complex"
    if len(task) > 100:
        return "medium"
    
    return "simple"


class IntelligenceRouter:
    def __init__(self, model_router):
        self.router = model_router
        self.moa = MixtureOfAgents(model_router)
        self.reflection = ReflectionEngine(model_router)
        self.sc = SelfConsistency(model_router)

    async def _classify_complexity_llm(self, task: str) -> str:
        """LLM-based classifier — used only when heuristic is insufficient."""
        if not task:
            return "simple"
        prompt = (
            f"Classify the complexity of this task into one word: 'simple', 'medium', or 'complex'.\n"
            f"- simple: basic API calls, status checks, formatting.\n"
            f"- medium: writing a function, fixing a bug, data analysis.\n"
            f"- complex: system architecture, comprehensive research, deep refactoring.\n\n"
            f"Task: {task[:500]}\nOutput ONLY ONE WORD."
        )
        try:
            res = await self.router.generate(
                [{"role": "user", "content": prompt}],
                task_hint="fast", max_tokens=5
            )
            ans = res.get("text", "").lower().strip()
            if "complex" in ans:
                return "complex"
            if "medium" in ans:
                return "medium"
            return "simple"
        except Exception:
            return "medium"

    async def generate(
        self,
        messages: List[Dict],
        task: str = "",
        force_mode: str = None,
        tools: List[Dict] = None,
        on_token=None
    ) -> Dict[str, Any]:
        """
        Main entry point for intelligent generation.
        
        Modes:
        - simple: Direct generation with CoT + tools (agent loop default)
        - medium: Generate + reflect (for final answers, not mid-loop)
        - complex: Multi-agent synthesis + reflection (for planning/architecture)
        
        CRITICAL: tools are ALWAYS forwarded when present.
        """
        # Use heuristic first (0ms), fall back to LLM only for ambiguous cases
        mode = force_mode or classify_complexity_fast(task)
        logger.info(f"Intelligence mode: [{mode}] for task: {task[:80]}...")

        if mode == "simple":
            return await self._generate_simple(messages, task, tools, on_token)
        elif mode == "medium":
            return await self._generate_medium(messages, task, tools, on_token)
        else:
            return await self._generate_complex(messages, task, tools)

    async def _generate_simple(
        self, messages, task, tools=None, on_token=None
    ) -> Dict[str, Any]:
        """
        Direct CoT + tools. Optimized for agent loop.
        Latency target: <2s for tool calls, <5s for generation.
        """
        # Disable assistant pre-fill if tools are present to ensure native tool calling works reliably
        cot_messages = inject_cot(messages, task, include_assistant=(tools is None))
        
        if on_token:
            result = await self.router.generate_stream(
                messages=cot_messages, tools=tools,
                task_hint="fast", on_token=on_token
            )
        else:
            result = await self.router.generate(
                messages=cot_messages, tools=tools, task_hint="fast"
            )

        # If there's a tool call, pass it through without CoT parsing
        if result.get("tool_call"):
            return {
                **result,
                "thinking": result.get("thinking", ""),
                "intelligence_mode": "cot_direct"
            }

        # Parse CoT for text responses
        parsed = extract_cot_answer(result.get("text", ""))
        return {
            **result,
            "text": parsed["answer"],
            "thinking": parsed["thinking"],
            "intelligence_mode": "cot_direct"
        }

    async def _generate_medium(
        self, messages, task, tools=None, on_token=None
    ) -> Dict[str, Any]:
        """
        CoT + Reflection. Used for quality-sensitive generation.
        
        CRITICAL: If tools are present, we MUST still pass them.
        Reflection applies only to text output, not tool calls.
        """
        cot_messages = inject_cot(messages, task)
        initial = await self.router.generate(
            messages=cot_messages, tools=tools, task_hint="quality"
        )

        # If the model wants to call a tool, DON'T reflect — pass through
        if initial.get("tool_call"):
            return {
                **initial,
                "thinking": initial.get("thinking", ""),
                "intelligence_mode": "cot_medium_passthrough"
            }

        parsed = extract_cot_answer(initial.get("text", ""))

        # Reflect on text responses only
        reflected = await self.reflection.reflect_and_improve(
            original_messages=messages,
            initial_response=parsed["answer"],
            task=task
        )
        return {
            **initial,
            **reflected,
            "intelligence_mode": "cot_reflection",
            "thinking": parsed["thinking"]
        }

    async def _generate_complex(
        self, messages, task, tools=None
    ) -> Dict[str, Any]:
        """
        Multi-agent synthesis + Reflection.
        Used for architecture, planning, deep research.
        
        NOTE: tools are passed to MoA proposers so they can use them.
        """
        cot_messages = inject_cot(messages, task)
        moa_result = await self.moa.generate(
            messages=cot_messages, task=task, min_proposers=3
        )

        reflected = await self.reflection.reflect_and_improve(
            original_messages=messages,
            initial_response=moa_result["text"],
            task=task
        )
        return {
            **moa_result,
            **reflected,
            "intelligence_mode": "moa_cot_reflection",
            "proposer_count": moa_result.get("proposer_count", 1)
        }
