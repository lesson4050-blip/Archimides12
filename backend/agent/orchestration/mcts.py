"""
Monte Carlo Tree Search (MCTS) / Hypothesis Testing Engine (V3).
Standardized and Integrated.
"""
import os
import uuid
import logging
import asyncio
import re
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from backend.agent.tdd_executor import TDDExecutor

logger = logging.getLogger(__name__)

class MCTSManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        # orchestrator should have llm and executor attributes
        self.tdd = TDDExecutor(orchestrator.llm, orchestrator.executor)
        self.max_depth = 2
        self.num_simulations = 3
        self.workspace_dir = "."

    def _run_git(self, cmd: List[str]) -> Tuple[bool, str]:
        try:
            full_cmd = ["git"] + cmd
            result = subprocess.run(
                full_cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                check=False
            )
            return (result.returncode == 0), (result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
        except Exception as e:
            return False, str(e)

    def is_git_repo(self) -> bool:
        success, _ = self._run_git(["status"])
        return success

    async def _evaluate_hypothesis(
        self,
        hypothesis: str,
        task: str,
        model_router: Any,
    ) -> Tuple[float, str]:
        """
        Реальная оценка гипотезы через LLM-scoring.
        Не запускает код — оценивает feasibility и completeness.
        """
        prompt = f"""Rate this approach to solving the task. Score 0.0-1.0.

TASK: {task[:400]}
APPROACH: {hypothesis[:500]}

Evaluate:
- Feasibility (0-1): Will this actually work?
- Completeness (0-1): Does it solve the full task?
- Risk (0-1, lower = better): What could go wrong?
- Efficiency (0-1): Is this the right number of steps?

Return JSON only:
{{"feasibility": 0.8, "completeness": 0.9, "risk": 0.2, "efficiency": 0.7,
  "overall": 0.8, "reason": "why this score"}}"""

        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            from backend.utils.json_repair import repair_and_parse
            data, _ = repair_and_parse(response.get("text", "{}"))
            if data and isinstance(data.get("overall"), (int, float)):
                score = float(data["overall"])
                reason = data.get("reason", "")
                return min(max(score, 0.0), 1.0), reason
        except Exception as e:
            logger.warning(f"MCTS evaluation failed: {e}")

        return 0.5, "evaluation failed"

    async def run_mcts(
        self,
        task: str,
        context: str,
        model_router: Any,
        executor_agent: Any,
        state: Any
    ) -> str:
        logger.info(f"MCTS: evaluating approaches for: {task[:60]}")

        # Generate N hypotheses
        prompt = (
            f"Task: {task}\nContext: {context[:300]}\n"
            "Generate 3 distinct technical approaches. "
            "Separate each with '---APPROACH---'."
        )
        response = await model_router.generate(
            messages=[{"role": "user", "content": prompt}],
            task_hint="think"
        )
        hypotheses = [
            h.strip()
            for h in response.get("text", "").split("---APPROACH---")
            if h.strip()
        ][:3]

        if not hypotheses:
            return task

        # Score all hypotheses in parallel
        scores = await asyncio.gather(*[
            self._evaluate_hypothesis(h, task, model_router)
            for h in hypotheses
        ])

        # Select best
        best_idx = max(range(len(scores)), key=lambda i: scores[i][0])
        best_hypothesis = hypotheses[best_idx]
        best_score, best_reason = scores[best_idx]

        logger.info(
            f"MCTS: selected approach {best_idx+1}/3 "
            f"(score={best_score:.2f}: {best_reason[:60]})"
        )

        return (
            f"OPTIMAL APPROACH (MCTS score {best_score:.2f}/1.0):\n"
            f"{best_hypothesis}"
        )
