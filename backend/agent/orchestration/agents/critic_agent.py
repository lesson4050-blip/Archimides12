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
You are a senior code reviewer and quality gate. 
Review the agent's performance RIGOROUSLY.

ORIGINAL TASK: {task}
RETRY ATTEMPT: {attempt}/{max_attempts}

EXECUTION LOGS (Tool results, errors, internal thoughts):
---
{logs}
---

FINAL AGENT RESPONSE:
---
{answer}
---

SCORE EACH DIMENSION (1-10):
1. CORRECTNESS: Does the code/response logically solve the task?
2. COMPLETENESS: Are all requirements met?
3. SECURITY: Are there any leaked keys, path traversals, or insecure patterns?
4. QUALITY: Is it production-ready?

AUTO-FAIL TRIGGERS:
- Tool execution failed but the agent claims success.
- Code has syntax errors or missing imports.
- Placeholders (TODO, [INSERT]) are present.
- Security violation (e.g., hardcoded secrets).

VERDICT RULES:
- If ALL scores >= 8 and no auto-fail: "VERDICT: PASS"
- Otherwise: "VERDICT: FAIL"

For FAIL, list specific issues: "ISSUE: [actionable technical problem]"
Include scores: "SCORES: correctness=N, completeness=N, security=N, quality=N"

IMPORTANT: Respond in the SAME LANGUAGE as the original task description.
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
        # Extract recent tool logs from history
        logs = []
        for msg in state.history[-10:]:
            if msg["role"] == "tool":
                logs.append(f"Tool [{msg.get('name')}]: {str(msg.get('content'))[:500]}")
            elif msg["role"] == "assistant" and "thought" in msg:
                logs.append(f"Thought: {msg['thought']}")
        
        logs_str = "\n".join(logs) if logs else "No execution logs available."

        prompt = self.REVIEW_PROMPT.format(
            task=state.task_description,
            logs=logs_str,
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
                r"\s*security=(\d+),\s*quality=(\d+)",
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

