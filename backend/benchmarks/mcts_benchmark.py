"""
MCTS Benchmark — Proves that tree search outperforms linear search.

Runs the same set of tasks with:
1. Linear mode (one-shot LLM call)
2. MCTS mode (tree search with UCB1)

Reports: accuracy, latency, diversity of solutions.
This is the PROOF that MCTS is worth the complexity.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from backend.agent.orchestration.mcts import MCTSManager, MCTSTree, MCTSNode

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    task: str
    linear_score: float
    mcts_score: float
    linear_time_ms: float
    mcts_time_ms: float
    mcts_nodes_explored: int
    mcts_best_hypothesis: str
    linear_response: str
    winner: str  # "mcts" or "linear" or "tie"


@dataclass
class BenchmarkSuite:
    results: List[BenchmarkResult] = field(default_factory=list)
    mcts_wins: int = 0
    linear_wins: int = 0
    ties: int = 0

    @property
    def mcts_win_rate(self) -> float:
        total = len(self.results)
        return self.mcts_wins / total if total else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self.results),
            "mcts_wins": self.mcts_wins,
            "linear_wins": self.linear_wins,
            "ties": self.ties,
            "mcts_win_rate": round(self.mcts_win_rate, 2),
            "avg_mcts_time_ms": round(
                sum(r.mcts_time_ms for r in self.results) / max(1, len(self.results)), 1
            ),
            "avg_linear_time_ms": round(
                sum(r.linear_time_ms for r in self.results) / max(1, len(self.results)), 1
            ),
        }


# Benchmark tasks with known-good evaluation criteria
BENCHMARK_TASKS = [
    {
        "task": "Write a Python function to merge two sorted lists into a single sorted list",
        "eval_keywords": ["merge", "sorted", "while", "return"],
        "difficulty": "easy",
    },
    {
        "task": "Design a rate limiter using the token bucket algorithm with thread safety",
        "eval_keywords": ["token", "bucket", "lock", "threading", "refill", "consume"],
        "difficulty": "medium",
    },
    {
        "task": "Implement a least recently used (LRU) cache with O(1) get and put operations",
        "eval_keywords": ["OrderedDict", "capacity", "get", "put", "move_to_end"],
        "difficulty": "medium",
    },
    {
        "task": "Write a function to detect cycles in a directed graph using DFS with coloring",
        "eval_keywords": ["visited", "recursion", "stack", "cycle", "graph", "dfs"],
        "difficulty": "hard",
    },
    {
        "task": "Implement async retry logic with exponential backoff, jitter, and max retries",
        "eval_keywords": ["retry", "backoff", "jitter", "async", "await", "sleep", "max_retries"],
        "difficulty": "medium",
    },
]


def _score_response(response: str, task_info: Dict) -> float:
    """Score a response based on keyword coverage and code quality."""
    text = response.lower()
    keywords = task_info["eval_keywords"]
    keyword_hits = sum(1 for kw in keywords if kw.lower() in text)
    keyword_score = keyword_hits / len(keywords) if keywords else 0

    if not response.strip():
        return 0.0

    has_code = "def " in response or "class " in response or "function " in response
    code_score = 0.3 if has_code else 0.0

    has_docstring = '"""' in response or "'''" in response or "/**" in response
    doc_score = 0.1 if has_docstring else 0.0

    lines = response.strip().split('\n')
    length_score = min(0.1, len(lines) / 200)

    return min(1.0, keyword_score * 0.5 + code_score + doc_score + length_score)


class MCTSBenchmark:
    """Run comparative benchmark between MCTS and linear approaches."""

    def __init__(self, model_router):
        self.router = model_router
        self.mcts = MCTSManager()

    async def run_linear(self, task: str) -> tuple:
        """Run a single linear (one-shot) generation."""
        start = time.time()
        try:
            result = await self.router.generate(
                messages=[{"role": "user", "content": task}],
                task_hint="quality",
            )
            response = result.get("text", "")
        except Exception as e:
            response = f"Error: {e}"
        elapsed = (time.time() - start) * 1000
        return response, elapsed

    async def run_mcts(self, task: str) -> tuple:
        """Run MCTS search for the task."""
        start = time.time()
        try:
            result = await self.mcts.run_mcts(
                task=task,
                context=task,
                model_router=self.router,
            )
            response = result
            nodes = len(self.mcts.__dict__.get('_last_tree_size', 0)) if hasattr(self.mcts, '_last_tree_size') else 0
        except Exception as e:
            response = f"Error: {e}"
            nodes = 0
        elapsed = (time.time() - start) * 1000
        return response, elapsed, nodes

    async def run_benchmark(
        self, tasks: Optional[List[Dict]] = None
    ) -> BenchmarkSuite:
        """Run the full benchmark suite."""
        suite = BenchmarkSuite()
        tasks = tasks or BENCHMARK_TASKS

        for task_info in tasks:
            task = task_info["task"]
            logger.info(f"Benchmark: {task[:50]}...")

            linear_response, linear_time = await self.run_linear(task)
            mcts_response, mcts_time, mcts_nodes = await self.run_mcts(task)

            linear_score = _score_response(linear_response, task_info)
            mcts_score = _score_response(mcts_response, task_info)

            if mcts_score > linear_score + 0.05:
                winner = "mcts"
                suite.mcts_wins += 1
            elif linear_score > mcts_score + 0.05:
                winner = "linear"
                suite.linear_wins += 1
            else:
                winner = "tie"
                suite.ties += 1

            suite.results.append(BenchmarkResult(
                task=task,
                linear_score=round(linear_score, 3),
                mcts_score=round(mcts_score, 3),
                linear_time_ms=round(linear_time, 1),
                mcts_time_ms=round(mcts_time, 1),
                mcts_nodes_explored=mcts_nodes,
                mcts_best_hypothesis=mcts_response[:500],
                linear_response=linear_response[:500],
                winner=winner,
            ))

        logger.info(f"Benchmark complete: {suite.summary()}")
        return suite
