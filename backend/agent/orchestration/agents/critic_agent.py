import logging
from typing import Optional, Callable, Dict, Any
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
    You are a Quality Assurance reviewer for an AI assistant called Archimedes.
    Review the following attempt at answering a user's request.
    
    LANGUAGE: ALWAYS RESPOND IN RUSSIAN.
    
    ORIGINAL TASK: {task}
    AGENT RESPONSE: {answer}
    
    REVIEW RULES:
    1. Be LENIENT. If the response is reasonable and addresses the task, it PASSES.
    2. Simple conversational responses (greetings, questions) ALWAYS PASS.
    3. LANGUAGE CHECK: The response must be in RUSSIAN unless English was explicitly requested. If it's in English, suggest translating it.
    4. Only FAIL if there are CRITICAL issues:
       - The response is completely off-topic or doesn't address the task at all
       - There are dangerous factual errors that could cause harm
       - The response is empty or gibberish
    5. Do NOT fail for:
       - Minor formatting issues
       - Incomplete but useful responses
       - Stylistic preferences
       - Missing minor details
    
    If it passes (which should be MOST of the time), respond with: VERDICT: PASS
    If it critically fails, list issues starting with 'ISSUE: '. Use RUSSIAN for your response.
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
            
            if "VERDICT: PASS" in review_text.upper() or "PASS" in review_text.upper():
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
                    await self.log_info(f"Accepting result (retry limit reached).", websocket_send)
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

