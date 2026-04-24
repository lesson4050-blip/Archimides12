"""
Monte Carlo Tree Search (MCTS) / Hypothesis Testing Engine (V3).

This module enables Archimedes to explore multiple parallel solutions
using Git branches, evaluate each path using TDD/execution feedback,
and select the optimal solution.
"""
import os
import uuid
import logging
import asyncio
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MCTSManager:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir

    def _run_git(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run a git command in the workspace."""
        try:
            full_cmd = ["git"] + cmd
            result = subprocess.run(
                full_cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    def is_git_repo(self) -> bool:
        """Check if workspace is a git repository."""
        success, _ = self._run_git(["status"])
        return success

    def create_branch(self, branch_name: str) -> bool:
        """Create and checkout a new git branch."""
        success, _ = self._run_git(["checkout", "-b", branch_name])
        return success

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout an existing git branch."""
        success, _ = self._run_git(["checkout", branch_name])
        return success

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        success, out = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return out if success else ""

    def commit_changes(self, message: str) -> bool:
        """Add all changes and commit."""
        self._run_git(["add", "."])
        success, _ = self._run_git(["commit", "-m", message])
        return success

    def merge_branch(self, branch_name: str) -> bool:
        """Merge a branch into the current branch."""
        success, _ = self._run_git(["merge", branch_name, "--no-edit"])
        return success

    def delete_branch(self, branch_name: str, force: bool = True) -> bool:
        """Delete a branch."""
        flag = "-D" if force else "-d"
        success, _ = self._run_git(["branch", flag, branch_name])
        return success

    async def generate_hypotheses(
        self,
        task: str,
        context: str,
        model_router: Any,
        session_id: str,
        num_branches: int = 3
    ) -> List[str]:
        """
        Ask the LLM to generate multiple distinct technical approaches for the task.
        """
        prompt = (
            f"You are an expert software architect. The user needs to solve this task:\n"
            f"<task>{task}</task>\n\n"
            f"Context:\n{context}\n\n"
            f"Provide {num_branches} COMPLETELY DISTINCT approaches to solving this problem.\n"
            f"For each approach, provide a brief summary and the specific steps to implement it.\n"
            f"Format your response EXACTLY as {num_branches} distinct blocks separated by '---APPROACH---'. "
            f"Do not include any other text outside these blocks."
        )

        response = await model_router.route(
            session_id=session_id,
            messages=[{"role": "user", "content": prompt}],
            task_hint="architect"
        )
        
        text = response.get("text", "")
        hypotheses = [h.strip() for h in text.split("---APPROACH---") if h.strip()]
        
        if not hypotheses:
            hypotheses = [task]  # Fallback to single path
            
        return hypotheses[:num_branches]

    async def execute_hypothesis(
        self,
        hypothesis: str,
        executor_agent: Any,
        state: Any,
        test_command: Optional[str] = None
    ) -> float:
        """
        Execute a single hypothesis using the provided executor agent.
        Returns a score (0.0 to 1.0) based on execution success and test passing.
        """
        score = 0.0
        
        # 1. Execute the hypothesis (this would modify the files in the current branch)
        state.task_description = hypothesis
        state.task_hint = "execute"
        # Reset step index for clean run
        state.current_step_index = 0
        
        try:
            # Run the agent loop until done (simplified for MCTS)
            for _ in range(10): # max 10 steps per hypothesis
                state = await executor_agent.process(state)
                if state.is_done:
                    score += 0.4  # Base score for successful completion
                    break
        except Exception as e:
            logger.error(f"Hypothesis execution failed: {e}")
            return 0.0

        # 2. Commit the changes
        self.commit_changes(f"Implemented hypothesis: {hypothesis[:50]}")

        # 3. Evaluate with tests if provided
        if test_command:
            try:
                # Use standard subprocess so it doesn't leak into the agent's active sandbox state improperly
                result = subprocess.run(
                    test_command,
                    shell=True,
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    score += 0.6  # Tests passed!
                else:
                    # Tests failed, but maybe some progress was made
                    # Calculate ratio of passed vs failed if possible, but for now 0 test score
                    pass
            except subprocess.TimeoutExpired:
                pass
        else:
            # If no tests, rely on agent's confidence
            score += 0.3

        return score

    async def run_mcts(
        self,
        task: str,
        context: str,
        model_router: Any,
        executor_agent: Any,
        state: Any,
        test_command: Optional[str] = None
    ) -> str:
        """
        Main MCTS entry point.
        1. Ensures git repo.
        2. Generates hypotheses.
        3. Branches out and executes each.
        4. Selects the best branch and merges it back to main.
        """
        if not self.is_git_repo():
            self._run_git(["init"])
            self.commit_changes("Initial commit for MCTS")

        base_branch = self.get_current_branch() or "main"
        
        hypotheses = await self.generate_hypotheses(
            task, context, model_router, state.session_id
        )
        
        logger.info(f"MCTS generated {len(hypotheses)} hypotheses.")
        
        results = []
        branches = []

        for i, hypothesis in enumerate(hypotheses):
            branch_name = f"mcts-branch-{uuid.uuid4().hex[:8]}"
            branches.append(branch_name)
            
            self.checkout_branch(base_branch)
            self.create_branch(branch_name)
            
            logger.info(f"Evaluating hypothesis {i+1} on branch {branch_name}")
            
            # Deep copy state if necessary, or just rely on the agent to manage it
            # We'll need a clean context for each branch
            executor_agent.context_manager.clear()
            
            score = await self.execute_hypothesis(
                hypothesis, executor_agent, state, test_command
            )
            
            results.append({
                "branch": branch_name,
                "score": score,
                "hypothesis": hypothesis
            })
            
            logger.info(f"Hypothesis {i+1} scored {score:.2f}")

        # Find the best branch
        best_result = max(results, key=lambda x: x["score"])
        
        logger.info(f"Best branch is {best_result['branch']} with score {best_result['score']:.2f}")
        
        # Checkout base and merge the best
        self.checkout_branch(base_branch)
        self.merge_branch(best_result["branch"])
        
        # Cleanup other branches
        for b in branches:
            if b != best_result["branch"]:
                self.delete_branch(b)
                
        return best_result["hypothesis"]
