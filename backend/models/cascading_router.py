"""
Cascading Intelligence Router — Adaptive Model Selection Engine.

Implements a tiered inference strategy that dramatically reduces cost and latency:
  - Tier 1 (Fast):    Groq / fast local model for trivial tasks (~50ms, ~$0.0001)
  - Tier 2 (Balanced): Gemini Flash for medium complexity (~500ms, ~$0.001)
  - Tier 3 (Deep):    Gemini Pro / Anthropic for complex reasoning (~3s, ~$0.01)

The router analyzes each request BEFORE sending it to any LLM and selects the
cheapest tier that can handle the task. If the fast tier returns a low-confidence
result, it automatically escalates to the next tier (cascading).

This closes the "5-10x token cost" and "latency" gaps from the audit.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TierMetrics:
    """Tracks per-tier performance for adaptive routing."""
    total_calls: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    escalations: int = 0  # Times this tier failed and escalated
    successes: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(1, self.total_calls)

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.total_calls)


# ── Complexity Signals ──────────────────────────────────────────────

# Tasks that NEVER need a heavy model
TRIVIAL_PATTERNS = [
    r"^(hi|hello|hey|привет|здравствуй|пока|спасибо|thanks)",
    r"^(what is|кто ты|как дела|что ты умеешь)",
    r"^\d+[\s]*[\+\-\*\/\%]\s*\d+",  # arithmetic
    r"^(translate|переведи)\s+.{1,100}$",  # short translation
]

# Tasks that ALWAYS need a heavy model
COMPLEX_PATTERNS = [
    r"(refactor|рефакторинг|architecture|архитектур)",
    r"(multi.?file|multiple files|несколько файлов)",
    r"(system design|проектирование системы)",
    r"(debug.*complex|отладить.*сложн)",
    r"(security audit|аудит безопасности)",
    r"(write.*test.*suite|написать.*набор.*тестов)",
    r"(analyze.*codebase|проанализировать.*код)",
]


def estimate_complexity(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    task_hint: str = "default"
) -> Tuple[str, float]:
    """
    Estimate task complexity without calling any LLM.
    
    Returns:
        (tier, confidence) where tier is 'fast', 'balanced', or 'deep'
        and confidence is 0.0-1.0 indicating routing certainty.
    """
    # Extract the latest user message
    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            break

    text_lower = user_text.lower().strip()
    text_len = len(user_text)
    num_tools = len(tools) if tools else 0
    num_messages = len(messages)

    # Signal 1: Explicit task hints
    if task_hint in ("quick", "fast", "simple", "summarize", "translate"):
        return "fast", 0.9

    if task_hint in ("think", "plan", "code", "debug", "execute"):
        return "deep", 0.8

    # Signal 2: Pattern matching
    for pattern in TRIVIAL_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "fast", 0.95

    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "deep", 0.9

    # Signal 3: Structural analysis
    has_code = bool(re.search(r'```|def |class |import |function |const |<[a-z]+>', user_text))
    has_multiple_steps = bool(re.search(r'\d+[\.\)]\s', user_text))
    has_urls = bool(re.search(r'https?://', user_text))

    complexity_score = sum([
        (text_len > 500) * 3,
        (text_len > 200) * 1,
        (num_tools > 3) * 3,
        (num_tools > 0) * 1,
        (num_messages > 10) * 2,
        has_code * 3,
        has_multiple_steps * 2,
        has_urls * 1,
    ])

    if complexity_score >= 6:
        return "deep", 0.7
    elif complexity_score >= 3:
        return "balanced", 0.6
    else:
        return "fast", 0.7


def should_escalate(response: Dict[str, Any], current_tier: str) -> bool:
    """
    Determine if the response quality warrants escalation to a higher tier.
    
    Escalation signals:
      - Very short response for a non-trivial question
      - Response contains uncertainty markers
      - Tool call failed
      - Model explicitly says it can't handle the task
    """
    if current_tier == "deep":
        return False  # Already at highest tier

    text = response.get("text", "")

    # Signal 1: Suspiciously short response
    if len(text) < 50 and current_tier == "fast":
        return True

    # Signal 2: Uncertainty markers
    uncertainty_markers = [
        "I'm not sure", "I cannot", "I don't know",
        "не уверен", "не могу", "не знаю",
        "beyond my capability", "need more context",
    ]
    text_lower = text.lower()
    if any(marker in text_lower for marker in uncertainty_markers):
        return True

    # Signal 3: Tool call failure
    tool_call = response.get("tool_call")
    if tool_call and response.get("error"):
        return True

    return False


class CascadingRouter:
    """
    Wraps the existing ModelRouter with cascading intelligence.
    
    Usage:
        cascade = CascadingRouter(model_router)
        result = await cascade.generate(messages, tools, task_hint)
        # Automatically picks cheapest tier, escalates if needed
    """

    def __init__(self, model_router):
        self.router = model_router
        self.metrics: Dict[str, TierMetrics] = {
            "fast": TierMetrics(),
            "balanced": TierMetrics(),
            "deep": TierMetrics(),
        }

    # Map tiers to task_hints that the existing ModelRouter understands
    TIER_HINTS = {
        "fast": "quick",
        "balanced": "default",
        "deep": "think",
    }

    TIER_ORDER = ["fast", "balanced", "deep"]

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        task_hint: str = "default",
        max_escalations: int = 1,
    ) -> Dict[str, Any]:
        """
        Generate a response using the cheapest adequate model tier.
        Escalates to heavier tiers if the response quality is insufficient.
        """
        tier, confidence = estimate_complexity(messages, tools, task_hint)
        tier_index = self.TIER_ORDER.index(tier)

        for attempt in range(max_escalations + 1):
            current_tier = self.TIER_ORDER[min(tier_index + attempt, len(self.TIER_ORDER) - 1)]
            effective_hint = self.TIER_HINTS[current_tier]
            metrics = self.metrics[current_tier]

            start = time.time()
            try:
                result = await self.router.generate(
                    messages=messages,
                    tools=tools,
                    task_hint=effective_hint,
                )
                elapsed_ms = (time.time() - start) * 1000
                metrics.total_calls += 1
                metrics.total_latency_ms += elapsed_ms
                metrics.total_tokens += result.get("usage", {}).get("total_tokens", 0)

                # Check if we should escalate
                if should_escalate(result, current_tier) and attempt < max_escalations:
                    metrics.escalations += 1
                    logger.info(
                        f"Cascading: {current_tier} → {self.TIER_ORDER[min(tier_index + attempt + 1, 2)]} "
                        f"(response quality insufficient)"
                    )
                    continue

                metrics.successes += 1
                result["_cascade_tier"] = current_tier
                result["_cascade_latency_ms"] = round(elapsed_ms, 1)
                result["_cascade_escalated"] = attempt > 0
                return result

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                metrics.total_calls += 1
                metrics.total_latency_ms += elapsed_ms
                metrics.escalations += 1
                logger.warning(f"Cascade tier {current_tier} failed: {e}")
                if attempt >= max_escalations:
                    logger.critical(f"All external LLM tiers failed. Triggering local Hydra fallback.")
                    try:
                        from backend.agent.orchestration.hydra_swarm import get_local_hydra
                        local_engine = get_local_hydra()
                        if local_engine:
                            hydra_result = await local_engine.generate(messages, tools)
                            hydra_result["_cascade_tier"] = "local_hydra"
                            hydra_result["_cascade_escalated"] = True
                            return hydra_result
                    except Exception as fallback_err:
                        logger.error(f"Local Hydra fallback also failed: {fallback_err}")
                    raise
                continue

        # Should never reach here, but fallback
        return await self.router.generate(messages=messages, tools=tools, task_hint="think")

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_token=None,
        task_hint: str = "default",
    ) -> Dict[str, Any]:
        """
        Streaming version of the cascading router.
        Note: Currently picks the best tier once and streams it.
        Cascading on stream failure is limited to ensure UX consistency.
        """
        tier, _ = estimate_complexity(messages, tools, task_hint)
        effective_hint = self.TIER_HINTS[tier]
        
        try:
            return await self.router.generate_stream(
                messages=messages,
                tools=tools,
                task_hint=effective_hint,
                on_token=on_token
            )
        except Exception as e:
            logger.warning(f"Cascading stream failed for tier {tier}: {e}. Falling back to non-stream.")
            return await self.generate(messages, tools, task_hint)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns cost/performance metrics for monitoring."""
        summary = {}
        for tier_name, m in self.metrics.items():
            summary[tier_name] = {
                "calls": m.total_calls,
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "success_rate": round(m.success_rate, 3),
                "escalation_rate": round(m.escalations / max(1, m.total_calls), 3),
                "total_tokens": m.total_tokens,
            }
        total_calls = sum(m.total_calls for m in self.metrics.values())
        fast_pct = self.metrics["fast"].total_calls / max(1, total_calls)
        summary["_efficiency"] = {
            "total_calls": total_calls,
            "fast_tier_pct": round(fast_pct * 100, 1),
            "estimated_cost_savings_pct": round(fast_pct * 70, 1),  # Fast tier ~70% cheaper
        }
        return summary
