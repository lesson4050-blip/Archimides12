import logging
from typing import Optional, Callable, Dict, Any
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

class CriticAgent(BaseAgent):
    """
    Quality gate. Reviews Executor's work and provides feedback or approval.
    """
    def __init__(self, router: ModelRouter):
        super().__init__("Critic", router)
        
    ATTACKER_PROMPT = """
    You are the Quality Assurance Agent (Critic) for Archimedes.
    Your task is to review the following attempt at solving a problem.
    
    ORIGINAL TASK: {task}
    AGENT ATTEMPT: {answer}
    
    CRITERIA:
    1. Is the task completely solved?
    2. Are there any factual errors or hallucinated data?
    3. Is the formatting correct (if specified)?
    
    If it is PERFECT, your response MUST contain the exact string: VERDICT: PASS
    If there are issues, list them clearly starting with 'ISSUE: '.
    """

    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        if not state.results:
            return state # Nothing to review
            
        last_result = state.results[-1].get("output", "")
        await self.log_info("Reviewing execution result for quality...", websocket_send)
        
        prompt = self.ATTACKER_PROMPT.format(task=state.task_description, answer=last_result)
        
        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            
            review_text = response.get("text", "")
            
            if "VERDICT: PASS" in review_text.upper():
                await self.log_thought("Result VERIFIED. Quality gate passed.", websocket_send)
                state.metadata["critic_verdict"] = "PASS"
                state.current_retry_count = 0 # Reset for next subtask if any
            else:
                # Issue detected
                issues = [line.replace("ISSUE:", "").strip() for line in review_text.split("\n") if line.startswith("ISSUE:")]
                if not issues: issues = [review_text]
                
                state.current_retry_count += 1
                await self.log_thought(f"Quality gate FAILED (Attempt {state.current_retry_count}/{state.critic_retry_limit}).", websocket_send)
                
                if state.current_retry_count >= state.critic_retry_limit:
                    await self.log_info(f"Reached max retry limit ({state.critic_retry_limit}). Accepting best effort result.", websocket_send)
                    state.metadata["critic_verdict"] = "LIMIT_REACHED"
                else:
                    # Provide feedback to Executor
                    feedback_msg = "Your previous attempt was rejected by the Quality Critic for the following reasons:\n"
                    feedback_msg += "\n".join([f"- {i}" for i in issues])
                    feedback_msg += "\nPlease try again and fix these specific issues."
                    
                    state.add_message("system", feedback_msg)
                    state.metadata["critic_verdict"] = "RETRY"
                    await self.log_info("Sent feedback to Executor for correction.", websocket_send)
                    
        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            state.metadata["critic_verdict"] = "ERROR_BYPASS" # Bypass on error to avoid hanging
            
        return state
