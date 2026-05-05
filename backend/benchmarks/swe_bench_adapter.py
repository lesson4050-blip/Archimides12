"""
SWE-bench Adapter v2 — Secure Sandbox Execution.
Archimedes Agent benchmarking engine.
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
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
    """Secure adapter that runs SWE-bench tasks inside isolated Docker sandboxes."""

    def __init__(self, orchestrator, sandbox_manager):
        self.orchestrator = orchestrator
        self.sandbox_manager = sandbox_manager
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    async def run_task(self, task: SWEBenchTask, timeout: int = 600) -> SWEBenchResult:
        """Run a single SWE-bench task inside a fresh sandbox session."""
        start = time.time()
        session_id = f"bench_{task.instance_id.replace('-', '_')}"
        
        try:
            # 1. Initialize Sandbox Session
            await self.sandbox_manager.create_session(session_id)
            executor = self.sandbox_manager.executor
            filesystem = self.sandbox_manager.filesystem

            # 2. Setup Environment inside Sandbox
            await executor.run_command(session_id, "git config --global user.email 'bench@archimedes.ai'")
            await executor.run_command(session_id, "git config --global user.name 'Archimedes Bench'")
            
            # 3. Clone and Checkout
            clone_cmd = f"git clone https://github.com/{task.repo} ."
            clone_res = await executor.run_command(session_id, clone_cmd)
            if not clone_res.get("success"):
                return SWEBenchResult(instance_id=task.instance_id, resolved=False, error=f"Clone failed: {clone_res.get('error')}")
            
            await executor.run_command(session_id, f"git checkout {task.base_commit}")

            # 4. Build Prompt
            prompt = self._build_prompt(task)

            # 5. Run Agent in the SAME session
            # We pass the session_id so the agent works in this specific container
            result = await asyncio.wait_for(
                self.orchestrator.run_task(prompt, session_id=session_id),
                timeout=timeout
            )

            # 6. Extract Agent's Patch (diff between base and current)
            diff_res = await executor.run_command(session_id, "git diff")
            agent_patch = diff_res.get("output", "")

            # 7. Apply verification tests
            if task.test_patch:
                await filesystem.write_file(session_id, "verification.patch", task.test_patch)
                await executor.run_command(session_id, "patch -p1 -i verification.patch")

            # 8. Run Tests
            test_res = await executor.run_command(session_id, "python3 -m pytest --tb=short -q")
            test_output = test_res.get("output", "")
            resolved = test_res.get("exit_code") == 0

            bench_result = SWEBenchResult(
                instance_id=task.instance_id,
                resolved=resolved,
                agent_patch=agent_patch,
                test_output=test_output,
                duration_seconds=time.time() - start,
                tokens_used=result.get("metadata", {}).get("tokens_used", 0)
            )
            self._save_result(bench_result)
            return bench_result

        except asyncio.TimeoutError:
            return SWEBenchResult(instance_id=task.instance_id, resolved=False, error=f"Timeout after {timeout}s", duration_seconds=time.time()-start)
        except Exception as e:
            logger.error(f"Bench task {task.instance_id} failed: {e}")
            return SWEBenchResult(instance_id=task.instance_id, resolved=False, error=str(e), duration_seconds=time.time()-start)
        finally:
            # 9. Cleanup Sandbox
            await self.sandbox_manager.destroy_session(session_id)

    def _build_prompt(self, task: SWEBenchTask) -> str:
        return f"""You are working on a real GitHub issue in an isolated environment.
Repository: {task.repo}
Instance: {task.instance_id}

## Problem Statement
{task.problem_statement}

## Instructions
1. Explore the codebase using the available tools.
2. Reproduce the issue if possible.
3. Fix the issue by modifying the files.
4. Verify your fix.
"""

    def _save_result(self, result: SWEBenchResult):
        result_path = RESULTS_DIR / f"{result.instance_id}.json"
        with open(result_path, "w") as f:
            json.dump({
                "instance_id": result.instance_id,
                "resolved": result.resolved,
                "duration_seconds": result.duration_seconds,
                "tokens_used": result.tokens_used,
                "error": result.error,
                "test_output": result.test_output[:5000],
            }, f, indent=2)

    async def run_batch(self, tasks: List[SWEBenchTask]) -> Dict[str, Any]:
        results = []
        for task in tasks:
            res = await self.run_task(task)
            results.append(res)
        
        resolved = sum(1 for r in results if r.resolved)
        return {
            "total": len(results),
            "resolved": resolved,
            "resolution_rate": round(resolved / len(results) * 100, 1) if results else 0,
            "results": [{"id": r.instance_id, "resolved": r.resolved} for r in results]
        }
