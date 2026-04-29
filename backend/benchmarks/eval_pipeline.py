"""
Evaluation Pipeline — Automated model comparison.

Runs a set of benchmark tasks against different models
and reports which model performs best for each category.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

EVAL_RESULTS_DIR = Path("data/eval_results")


@dataclass
class EvalTask:
    """A single evaluation task."""
    id: str
    category: str
    prompt: str
    expected_contains: List[str] = field(default_factory=list)
    max_tokens: int = 1000
    timeout: int = 60


@dataclass
class EvalResult:
    """Result of running one task on one model."""
    task_id: str
    model: str
    success: bool
    response: str = ""
    latency_ms: int = 0
    tokens_used: int = 0
    error: str = ""


BUILTIN_TASKS = [
    EvalTask(id="code_1", category="code", prompt="Write a Python function that checks if a string is a palindrome. Return only the function.", expected_contains=["def ", "return"]),
    EvalTask(id="code_2", category="code", prompt="Write a Python function to find the nth Fibonacci number using memoization.", expected_contains=["def ", "return"]),
    EvalTask(id="debug_1", category="debug", prompt="This code has a bug: `def add(a, b): return a - b`. What is the bug and how to fix it?", expected_contains=["+"]),
    EvalTask(id="plan_1", category="plan", prompt="Plan how to add user authentication to a FastAPI app. List the steps.", expected_contains=["JWT", "password"]),
    EvalTask(id="refactor_1", category="refactor", prompt="Refactor this: `if x == True: return True\\nelse: return False` into a single line.", expected_contains=["return x"]),
]


class EvalPipeline:
    """Run evaluation tasks across models and compare."""

    def __init__(self, router):
        self.router = router
        EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    async def run_task(self, task: EvalTask, model_hint: str) -> EvalResult:
        start = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self.router.generate(messages=[{"role": "user", "content": task.prompt}], task_hint=model_hint),
                timeout=task.timeout
            )
            text = resp.get("text", "")
            latency = int((time.monotonic() - start) * 1000)
            success = all(expected.lower() in text.lower() for expected in task.expected_contains) if task.expected_contains else len(text) > 10
            return EvalResult(task_id=task.id, model=model_hint, success=success, response=text[:500], latency_ms=latency, tokens_used=resp.get("tokens_used", 0))
        except Exception as e:
            return EvalResult(task_id=task.id, model=model_hint, success=False, error=str(e), latency_ms=int((time.monotonic() - start) * 1000))

    async def run_all(self, tasks: Optional[List[EvalTask]] = None, models: Optional[List[str]] = None) -> Dict[str, Any]:
        tasks = tasks or BUILTIN_TASKS
        models = models or ["fast", "code", "default", "think"]
        results = []
        for model in models:
            for task in tasks:
                result = await self.run_task(task, model)
                results.append(result)
                logger.info(f"Eval: {task.id} on {model} -> {'PASS' if result.success else 'FAIL'} ({result.latency_ms}ms)")
        summary = {}
        for model in models:
            model_results = [r for r in results if r.model == model]
            summary[model] = {
                "total": len(model_results),
                "passed": sum(1 for r in model_results if r.success),
                "avg_latency_ms": round(sum(r.latency_ms for r in model_results) / max(len(model_results), 1)),
                "success_rate": round(sum(1 for r in model_results if r.success) / max(len(model_results), 1) * 100, 1)
            }
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "models_tested": models, "total_tasks": len(tasks),
            "summary": summary,
            "best_model": max(summary, key=lambda m: summary[m]["success_rate"]),
            "results": [{"task": r.task_id, "model": r.model, "success": r.success, "latency_ms": r.latency_ms, "error": r.error} for r in results]
        }
        result_path = EVAL_RESULTS_DIR / f"eval_{int(time.time())}.json"
        with open(result_path, "w") as f:
            json.dump(report, f, indent=2)
        return report
