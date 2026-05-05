import logging
from typing import Optional, List, Dict, Any
from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState, AgentMode
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    """
    Strategic Manager for Archimedes.
    Reviews the entire history, detects loops, and adjusts routing strategies.
    Does not write code. Decides HOW to work.
    """

    SUPERVISOR_PROMPT = """
You are the PRINCIPAL ARCHITECT of Archimedes AI. 
Review the current task progress and decide if we need a strategy shift.

TASK: {task}
CURRENT STRATEGY: {strategy}
RETRY COUNT: {retry_count}

LAST 5 EVENTS:
{history_summary}

ANALYSIS REQUIREMENTS:
1. DETECT LOOPS: Is the agent repeating the same mistake?
2. EVALUATE STRATEGY: Is the current strategy (e.g., swarm_code) appropriate for the errors encountered?
3. DECIDE: Should we continue, or SWITCH to a different strategy?

STRATEGIES:
- swarm_code: Multi-file implementation.
- swarm_research: Web search and documentation analysis.
- codeact: Fast single-file debugging.
- mcts: Exploration of multiple alternative paths.

OUTPUT ONLY VALID JSON:
{{
  "analysis": "Brief analysis of progress",
  "loop_detected": true/false,
  "action": "CONTINUE" or "SWITCH",
  "new_strategy": "strategy_name",
  "reasoning": "Why this action?"
}}
"""

    def __init__(self, router: ModelRouter):
        super().__init__("Supervisor", router)

    async def process(self, state: OrchestrationState) -> OrchestrationState:
        # Only trigger if we have at least one retry or a high-complexity task
        if state.current_retry_count == 0 and len(state.results) < 3:
            return state

        logger.info(f"[{state.session_id}] Supervisor: Auditing progress...")

        # Build history summary (last 5 messages)
        history_summary = []
        for msg in state.history[-5:]:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:200]
            history_summary.append(f"[{role}]: {content}...")

        prompt = self.SUPERVISOR_PROMPT.format(
            task=state.task_description,
            strategy=state.metadata.get("strategy", "unknown"),
            retry_count=state.current_retry_count,
            history_summary="\n".join(history_summary)
        )

        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think" # High-level reasoning
            )
            
            from backend.utils.json_repair import repair_and_parse
            decision, _ = repair_and_parse(response.get("text", "{}"))
            
            if decision.get("action") == "SWITCH":
                old_strat = state.metadata.get("strategy")
                new_strat = decision.get("new_strategy")
                state.metadata["strategy"] = new_strat
                state.metadata["supervisor_intervention"] = True
                
                msg = f"🔄 Supervisor Intervention: Switching strategy from {old_strat} to {new_strat}. Reasoning: {decision.get('reasoning')}"
                state.add_message("system", msg)
                logger.info(f"[{state.session_id}] Supervisor: {msg}")
            
            if decision.get("loop_detected"):
                state.add_message("system", "⚠️ Loop detected. Supervisor suggests backtracking or using a different tool.")

        except Exception as e:
            logger.error(f"Supervisor processing failed: {e}")

        return state
