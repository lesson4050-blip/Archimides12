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

    async def _evaluate_branch_with_tdd(self, branch_name: str, task: str) -> Tuple[float, str]:
        """Runs TDD cycle on branch and returns score based on test results."""
        logger.info(f"MCTS: Evaluating branch {branch_name} with TDD...")
        session_id = f"mcts_{branch_name}"
        
        # In a real scenario, we might want to pass initial code if already generated
        result_text = await self.tdd.execute_tdd(
            task=task,
            session_id=session_id,
            code_path="implementation.py"
        )
        
        if "[TDD Success]" in result_text:
            # Extract coverage or just give a high score
            cov_match = re.search(r"coverage: (\d+)%", result_text)
            coverage = int(cov_match.group(1)) if cov_match else 80
            score = 0.5 + (coverage / 200.0) # 0.5 to 1.0
            return score, result_text
        else:
            return 0.1, result_text

    async def run_mcts(
        self,
        task: str,
        context: str,
        model_router: Any,
        executor_agent: Any,
        state: Any
    ) -> str:
        """
        The main entry point called by Orchestrator.
        Explores multiple paths via Git branches and returns the best solution.
        """
        logger.info(f"Starting MCTS for task: {task}")
        
        if not self.is_git_repo():
            logger.info("Initializing git repo for MCTS exploration.")
            self._run_git(["init"])
            self._run_git(["add", "."])
            self._run_git(["commit", "-m", "Initial commit for MCTS"])

        base_branch = "main" # Assume main for simplicity, or detect current
        
        # 1. Generate Hypotheses
        prompt = (
            f"Task: {task}\nContext: {context}\n"
            "Generate 3 distinct technical approaches. Separate by '---APPROACH---'."
        )
        response = await model_router.generate(
            messages=[{"role": "user", "content": prompt}],
            task_hint="think"
        )
        hypotheses = [h.strip() for h in response.get("text", "").split("---APPROACH---") if h.strip()]
        
        if not hypotheses:
            return "No distinct hypotheses generated. Proceeding with default."

        results = []
        for i, hyp in enumerate(hypotheses[:3]):
            branch_name = f"archimedes-branch-{uuid.uuid4().hex[:6]}"
            logger.info(f"Exploring Hypothesis {i+1} on branch {branch_name}")
            
            # Switch to new branch
            self._run_git(["checkout", "-b", branch_name])
            
            # 4. Evaluate branch using TDD
            score, feedback = await self._evaluate_branch_with_tdd(branch_name, task)
            
            results.append({
                "hypothesis": hyp,
                "branch": branch_name,
                "score": score,
                "feedback": feedback
            })
            
            # Return to base
            self._run_git(["checkout", base_branch])

        # 2. Select Best (Simple max for now)
        best = max(results, key=lambda x: x["score"])
        
        # 3. Merge Best
        logger.info(f"Merging best branch: {best['branch']}")
        self._run_git(["merge", best["branch"], "--no-edit"])
        
        return f"Selected Approach: {best['hypothesis']}\nResult: Successfully merged code changes from {best['branch']}."
