"""
SWE-bench Adapter — Run Archimedes against SWE-bench tasks.

Format:
  instance_id, repo, base_commit, problem_statement,
  patch (gold), test_patch (verification tests)

Pipeline:
1. Clone repo at base_commit
2. Send problem_statement to Archimedes orchestrator
3. Capture agent's patch
4. Apply test_patch and run tests
5. Report pass/fail
"""
import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RESULTS_DIR = Path("data/swe_bench_results")


@dataclass
class SWEBenchTask:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str = ""
    test_patch: str = ""
    patch: str = ""
    version: str = ""


@dataclass
class SWEBenchResult:
    instance_id: str
    resolved: bool
    agent_patch: str = ""
    test_output: str = ""
    duration_seconds: float = 0.0
    tokens_used: int = 0
    error: str = ""


class SWEBenchAdapter:
    """Adapter to run Archimedes on SWE-bench evaluation tasks."""

    def __init__(self, orchestrator, workspace_base: str = "/tmp/swe_bench"):
        self.orchestrator = orchestrator
        self.workspace_base = workspace_base
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    async def run_task(
        self, task: SWEBenchTask, timeout: int = 300
    ) -> SWEBenchResult:
        """Run a single SWE-bench task."""
        start = time.time()
        repo_dir = os.path.join(self.workspace_base, task.instance_id)

        try:
            # Clone repo at base commit
            os.makedirs(repo_dir, exist_ok=True)
            clone_result = subprocess.run(
                ["git", "clone", f"https://github.com/{task.repo}", repo_dir],
                capture_output=True, text=True, timeout=60
            )
            if clone_result.returncode != 0:
                return SWEBenchResult(
                    instance_id=task.instance_id, resolved=False,
                    error=f"Clone failed: {clone_result.stderr[:200]}"
                )

            subprocess.run(
                ["git", "checkout", task.base_commit],
                cwd=repo_dir, capture_output=True, timeout=30
            )

            # Build prompt for agent
            prompt = self._build_prompt(task, repo_dir)

            # Run agent
            result = await asyncio.wait_for(
                self.orchestrator.run_task(prompt, mode="omega_codeact"),
                timeout=timeout
            )

            # Get agent's patch
            diff_result = subprocess.run(
                ["git", "diff"], cwd=repo_dir,
                capture_output=True, text=True, timeout=10
            )
            agent_patch = diff_result.stdout

            # Apply test patch and run tests
            if task.test_patch:
                with open("/tmp/test.patch", "w") as f:
                    f.write(task.test_patch)
                subprocess.run(
                    ["patch", "-p1", "-i", "/tmp/test.patch"],
                    cwd=repo_dir, capture_output=True, timeout=30
                )

            test_result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q"],
                cwd=repo_dir, capture_output=True, text=True, timeout=120
            )
            test_output = test_result.stdout + test_result.stderr
            resolved = test_result.returncode == 0

            swe_result = SWEBenchResult(
                instance_id=task.instance_id,
                resolved=resolved,
                agent_patch=agent_patch,
                test_output=test_output,
                duration_seconds=time.time() - start,
            )
            self._save_result(swe_result)
            return swe_result

        except asyncio.TimeoutError:
            return SWEBenchResult(
                instance_id=task.instance_id, resolved=False,
                error=f"Timeout after {timeout}s",
                duration_seconds=time.time() - start
            )
        except Exception as e:
            return SWEBenchResult(
                instance_id=task.instance_id, resolved=False,
                error=str(e), duration_seconds=time.time() - start
            )
        finally:
            import shutil
            shutil.rmtree(repo_dir, ignore_errors=True)

    def _build_prompt(self, task: SWEBenchTask, repo_dir: str) -> str:
        prompt = f"""Repository: {task.repo}
Commit: {task.base_commit}
Working directory: {repo_dir}

## Problem Statement
{task.problem_statement}
"""
        if task.hints_text:
            prompt += f"\n## Hints\n{task.hints_text}\n"
        prompt += """
## Instructions
1. Analyze the problem statement carefully
2. Explore the repository to understand the relevant code
3. Identify the root cause
4. Generate a minimal fix
5. Run tests to verify
"""
        return prompt

    def _save_result(self, result: SWEBenchResult):
        result_path = RESULTS_DIR / f"{result.instance_id}.json"
        with open(result_path, "w") as f:
            json.dump({
                "instance_id": result.instance_id,
                "resolved": result.resolved,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
                "test_output": result.test_output[:2000],
            }, f, indent=2)

    async def run_batch(
        self, tasks: List[SWEBenchTask], max_concurrent: int = 2
    ) -> Dict[str, Any]:
        """Run multiple SWE-bench tasks sequentially."""
        results = []
        for task in tasks:
            result = await self.run_task(task)
            results.append(result)
            logger.info(
                f"SWE-bench {task.instance_id}: "
                f"{'RESOLVED' if result.resolved else 'FAILED'}"
            )
        resolved = sum(1 for r in results if r.resolved)
        return {
            "total": len(results),
            "resolved": resolved,
            "resolution_rate": round(resolved / max(len(results), 1) * 100, 1),
            "avg_duration": round(
                sum(r.duration_seconds for r in results) / max(len(results), 1), 1
            ),
            "results": [
                {"id": r.instance_id, "resolved": r.resolved, "error": r.error}
                for r in results
            ],
        }


def load_swe_bench_tasks(dataset_path: str) -> List[SWEBenchTask]:
    """Load tasks from SWE-bench JSONL dataset."""
    tasks = []
    with open(dataset_path) as f:
        for line in f:
            data = json.loads(line)
            tasks.append(SWEBenchTask(
                instance_id=data["instance_id"],
                repo=data["repo"],
                base_commit=data["base_commit"],
                problem_statement=data["problem_statement"],
                hints_text=data.get("hints_text", ""),
                test_patch=data.get("test_patch", ""),
                patch=data.get("patch", ""),
                version=data.get("version", ""),
            ))
    return tasks
