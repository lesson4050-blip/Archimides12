import logging
from typing import Optional, Callable
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

class CriticAgent(BaseAgent):
    """
    Quality gate. Reviews Executor's work and provides feedback or approval.
    Designed to be lenient — only rejects for critical errors, not stylistic issues.
    """
    def __init__(self, router: ModelRouter):
        super().__init__("Critic", router)
        
    ATTACKER_PROMPT = """
You are a strict Quality Gate for Archimedes AI.
Review this agent response RIGOROUSLY.

ORIGINAL TASK: {task}
AGENT RESPONSE: {answer}

FAIL immediately if ANY of these are true:
1. Response is in wrong language (must be RUSSIAN unless English asked)
2. Response claims to do X but clearly does NOT do X
3. Code is present but obviously broken (syntax errors, wrong logic)
4. Response is empty, "I don't know", or refuses without reason
5. Response addresses a DIFFERENT task than requested
6. Response contains placeholder text like TODO, [INSERT], etc.
7. Response is less than 20% complete relative to task complexity

PASS if:
- Response genuinely addresses the task (even if imperfect)
- Response is in correct language
- Response shows real work/reasoning

Be LENIENT on style, formatting, minor details.
Be STRICT on correctness and completeness.

If PASS: output exactly "VERDICT: PASS"
If FAIL: output "ISSUE: [specific problem]" for each issue.
Respond in RUSSIAN.
"""

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        if not state.results:
            return state # Nothing to review
            
        last_result = state.results[-1].get("output", "")
        
        # Skip critic for short/conversational responses
        if len(last_result.strip()) < 200:
            logger.info("[Critic] Short response — auto-passing quality gate")
            state.metadata["critic_verdict"] = "PASS"
            return state
        
        await self.log_info("Reviewing execution result for quality...", websocket_send)
        
        # Truncate very long responses to avoid overloading the LLM
        truncated_answer = last_result[:2000] + ("..." if len(last_result) > 2000 else "")
        prompt = self.ATTACKER_PROMPT.format(task=state.task_description, answer=truncated_answer)
        
        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            
            review_text = response.get("text", "")
            
            import re
            is_pass = bool(re.search(r"VERDICT:\s*PASS", review_text, re.IGNORECASE))
            has_issues = bool(re.search(r"ISSUE:", review_text, re.IGNORECASE))
            
            if is_pass and not has_issues:
                await self.log_thought("Result VERIFIED. Quality gate passed.", websocket_send)
                state.metadata["critic_verdict"] = "PASS"
                state.current_retry_count = 0
            else:
                # Issue detected
                issues = [line.replace("ISSUE:", "").strip() for line in review_text.split("\n") if line.strip().startswith("ISSUE:")]
                if not issues: issues = [review_text[:200]]
                
                state.current_retry_count += 1
                max_retries = min(state.critic_retry_limit, 1)  # Cap at 1 retry to save compute
                await self.log_thought(f"Quality gate flagged issues (Attempt {state.current_retry_count}/{max_retries}).", websocket_send)
                
                if state.current_retry_count >= max_retries:
                    await self.log_info("Accepting result (retry limit reached).", websocket_send)
                    state.metadata["critic_verdict"] = "LIMIT_REACHED"
                else:
                    feedback_msg = "The Quality Critic noted:\n"
                    feedback_msg += "\n".join([f"- {i}" for i in issues])
                    feedback_msg += "\nPlease address these if possible."
                    
                    state.add_message("system", feedback_msg)
                    state.metadata["critic_verdict"] = "RETRY"
                    await self.log_info("Sent feedback to Executor for correction.", websocket_send)
                    
        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            state.metadata["critic_verdict"] = "ERROR_BYPASS"
            
        return state

