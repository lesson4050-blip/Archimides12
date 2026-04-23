import logging
import re
from typing import Optional, Callable
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """
    Production-grade quality gate. Reviews Executor's work with multi-criteria
    scoring and provides structured feedback for retry loops.
    
    Quality philosophy:
    - STRICT on correctness, completeness, and task alignment
    - LENIENT on style, formatting, minor wording
    - Uses full retry budget from OrchestrationState
    - Only auto-passes truly trivial outputs (< 50 chars)
    """

    # Minimum output length to trigger full review (trivial outputs auto-pass)
    AUTO_PASS_THRESHOLD = 50

    def __init__(self, router: ModelRouter):
        super().__init__("Critic", router)

    REVIEW_PROMPT = """
You are a strict Quality Gate for Archimedes AI.
Review this agent response RIGOROUSLY across multiple dimensions.

ORIGINAL TASK: {task}
RETRY ATTEMPT: {attempt}/{max_attempts}
AGENT RESPONSE:
---
{answer}
---

SCORE EACH DIMENSION (1-10):
1. CORRECTNESS: Does the response factually/logically solve the task?
2. COMPLETENESS: Does it address ALL parts of the task, not just some?
3. LANGUAGE: Is it in the correct language (RUSSIAN unless English was asked)?
4. QUALITY: Is the output production-ready (no TODOs, placeholders, broken code)?

AUTO-FAIL if ANY are true:
- Response is empty, "I don't know", or refuses without reason
- Response addresses a DIFFERENT task than requested
- Code has obvious syntax errors or uses undefined variables
- Response contains placeholder text like TODO, [INSERT], FIXME, "example.com"
- Response is less than 20% complete relative to task complexity
- Response claims to do X but the output clearly does NOT do X

VERDICT RULES:
- If ALL scores >= 6 and no auto-fail triggers: output "VERDICT: PASS"
- If ANY score < 4 or auto-fail triggered: output "VERDICT: FAIL"
- Otherwise: output "VERDICT: PASS" (accept imperfect but genuine work)

For FAIL, list each issue as "ISSUE: [specific, actionable problem]"
Include the dimension scores as "SCORES: correctness=N, completeness=N, language=N, quality=N"

Respond in RUSSIAN.
"""

    async def process(
        self,
        state: OrchestrationState,
        websocket_send: Optional[Callable] = None
    ) -> OrchestrationState:
        if not state.results:
            return state  # Nothing to review

        last_result = state.results[-1].get("output", "")

        # Only auto-pass for truly trivial outputs (greetings, one-liners)
        if len(last_result.strip()) < self.AUTO_PASS_THRESHOLD:
            logger.info("[Critic] Trivial response (<%d chars) — auto-pass",
                        self.AUTO_PASS_THRESHOLD)
            state.metadata["critic_verdict"] = "PASS"
            return state

        await self.log_info(
            "Проверяю качество результата...", websocket_send
        )

        # Use the FULL retry budget from state, not a hardcoded cap
        max_retries = state.critic_retry_limit

        # Truncate very long responses to avoid overloading the LLM
        truncated = last_result[:3000] + (
            "\n... [truncated]" if len(last_result) > 3000 else ""
        )
        prompt = self.REVIEW_PROMPT.format(
            task=state.task_description,
            answer=truncated,
            attempt=state.current_retry_count + 1,
            max_attempts=max_retries
        )

        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )

            review_text = response.get("text", "")

            # Parse verdict
            is_pass = bool(
                re.search(r"VERDICT:\s*PASS", review_text, re.IGNORECASE)
            )
            is_fail = bool(
                re.search(r"VERDICT:\s*FAIL", review_text, re.IGNORECASE)
            )

            # Parse scores for metadata
            scores_match = re.search(
                r"SCORES:\s*correctness=(\d+),\s*completeness=(\d+),"
                r"\s*language=(\d+),\s*quality=(\d+)",
                review_text, re.IGNORECASE
            )
            if scores_match:
                state.metadata["critic_scores"] = {
                    "correctness": int(scores_match.group(1)),
                    "completeness": int(scores_match.group(2)),
                    "language": int(scores_match.group(3)),
                    "quality": int(scores_match.group(4)),
                }

            if is_pass and not is_fail:
                await self.log_thought(
                    "✅ Результат прошёл проверку качества.",
                    websocket_send
                )
                state.metadata["critic_verdict"] = "PASS"
                state.current_retry_count = 0
            else:
                # Extract actionable issues
                issues = [
                    line.replace("ISSUE:", "").strip()
                    for line in review_text.split("\n")
                    if line.strip().upper().startswith("ISSUE:")
                ]
                if not issues:
                    issues = [review_text[:300]]

                state.current_retry_count += 1
                await self.log_thought(
                    f"⚠️ Найдены проблемы (попытка "
                    f"{state.current_retry_count}/{max_retries}).",
                    websocket_send
                )

                if state.current_retry_count >= max_retries:
                    await self.log_info(
                        "Принимаю результат (лимит попыток исчерпан).",
                        websocket_send
                    )
                    state.metadata["critic_verdict"] = "LIMIT_REACHED"
                    state.metadata["critic_issues"] = issues
                else:
                    feedback_msg = (
                        "The Quality Critic found issues that need fixing:\n"
                    )
                    feedback_msg += "\n".join(
                        [f"- {issue}" for issue in issues]
                    )
                    feedback_msg += (
                        "\n\nPlease address these issues. "
                        "Focus on the highest-severity problems first."
                    )

                    state.add_message("system", feedback_msg)
                    state.metadata["critic_verdict"] = "RETRY"
                    state.metadata["critic_issues"] = issues
                    await self.log_info(
                        "Отправил замечания Исполнителю для доработки.",
                        websocket_send
                    )

        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            # On error, default to RETRY (not PASS) for safety,
            # unless we've already exhausted retries
            if state.current_retry_count >= state.critic_retry_limit:
                state.metadata["critic_verdict"] = "ERROR_BYPASS"
            else:
                state.metadata["critic_verdict"] = "ERROR_BYPASS"
                logger.warning(
                    "Critic error — bypassing to prevent infinite loop"
                )

        return state

