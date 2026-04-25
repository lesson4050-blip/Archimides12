"""
Archimedes Benchmark Runner.
Runs the agent on a test suite and reports scores.
"""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Internal benchmark tasks for quick self-evaluation
QUICK_BENCHMARK_TASKS = [
    {
        "id": "code_001",
        "task": "Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes. Include docstring and test it with n=50.",
        "category": "code_generation",
        "expected_contains": ["def ", "yield", "return", "prime"]
    },
    {
        "id": "debug_001", 
        "task": "Fix this Python code:\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\nfib_list = [fibonacci(i) for i in range(100)]\n# This is too slow, fix it with memoization",
        "category": "debugging",
        "expected_contains": ["cache", "lru_cache", "memo"]
    },
    {
        "id": "research_001",
        "task": "What is the current state-of-the-art performance on SWE-bench verified as of 2026?",
        "category": "research",
        "expected_contains": ["%", "bench", "resolve"]
    },
    {
        "id": "file_001",
        "task": "Create a file called hello_archimedes.py with a function greet(name) that returns 'Hello, {name}! I am Archimedes.' Then run it with name='World'.",
        "category": "file_ops",
        "expected_contains": ["Hello", "Archimedes"]
    },
]


class BenchmarkRunner:
    def __init__(self, agent):
        self.agent = agent
        self.results = []
    
    async def run_quick_benchmark(self) -> Dict[str, Any]:
        """Run quick internal benchmark and return scores."""
        start = time.time()
        scores = []
        
        for task_def in QUICK_BENCHMARK_TASKS:
            task_start = time.time()
            try:
                result = await asyncio.wait_for(
                    self.agent.process_task(task_def["task"]),
                    timeout=120
                )
                output = str(result.output or "").lower()
                success = result.status.value == "completed"
                
                # Check expected keywords
                keyword_score = sum(
                    1 for kw in task_def["expected_contains"]
                    if kw.lower() in output
                ) / len(task_def["expected_contains"])
                
                final_score = 1.0 if (success and keyword_score >= 0.5) else keyword_score * 0.5
                
            except asyncio.TimeoutError:
                final_score = 0.0
                success = False
            except Exception as e:
                final_score = 0.0
                success = False
            
            scores.append({
                "id": task_def["id"],
                "category": task_def["category"],
                "score": final_score,
                "success": success,
                "duration": time.time() - task_start
            })
        
        total_score = sum(s["score"] for s in scores) / len(scores) * 100
        
        return {
            "total_score": round(total_score, 1),
            "total_duration": time.time() - start,
            "tasks": scores,
            "summary": f"{total_score:.1f}% ({sum(1 for s in scores if s['success'])}/{len(scores)} passed)"
        }
