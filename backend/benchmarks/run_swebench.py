"""
SWE-bench Runner for Archimedes
Executes tasks from the SWE-bench dataset against the AgentOrchestrator
for performance evaluation.
"""
import asyncio
import json
import os
import argparse
from typing import Dict, Any

from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.agent.orchestration.state import OrchestrationState


async def run_benchmark(dataset_path: str, limit: int = 10, output_dir: str = "output/benchmarks"):
    """
    Run Archimedes against a subset of SWE-bench.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading dataset from {dataset_path}...")
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        return

    tasks = tasks[:limit]
    print(f"Running {len(tasks)} tasks...")

    from backend.models.model_router import ModelRouter
    from backend.agent.tool_registry import ToolRegistry
    from backend.memory.context_manager import ContextManager
    
    router = ModelRouter()
    tools = ToolRegistry()
    ctx = ContextManager()
    
    orchestrator = AgentOrchestrator(router, tools, ctx)
    results = []

    for idx, task in enumerate(tasks):
        instance_id = task.get("instance_id", f"task_{idx}")
        problem_statement = task.get("problem_statement", "")
        repo = task.get("repo", "unknown/repo")
        base_commit = task.get("base_commit", "")
        
        print(f"\n[{idx+1}/{len(tasks)}] Executing {instance_id} ({repo} @ {base_commit[:7]})")
        
        # Build prompt mimicking the SWE-bench environment
        prompt = (
            f"You are resolving an issue in the repository {repo}.\n"
            f"The repository is checked out at commit {base_commit}.\n\n"
            f"Issue Description:\n{problem_statement}\n\n"
            "Please analyze the problem, locate the relevant files, "
            "write a fix, and verify it using available tests."
        )

        state = OrchestrationState(
            task_description=prompt,
            session_id=f"bench_{instance_id}"
        )

        # Execute
        try:
            final_state = await orchestrator.run_task(
                task_description=prompt,
                session_id=f"bench_{instance_id}"
            )
            
            result = {
                "instance_id": instance_id,
                "status": final_state.get("status", "UNKNOWN"),
                "steps_taken": len(final_state.get("history", [])),
                "tokens_used": final_state.get("total_token_usage", 0),
                "final_answer": final_state.get("final_answer", ""),
                "confidence_score": final_state.get("confidence_score", 0.0)
            }
            print(f"Task finished with status: {result['status']}")
            
        except Exception as e:
            print(f"Task {instance_id} crashed: {e}")
            result = {
                "instance_id": instance_id,
                "status": "CRASHED",
                "error": str(e)
            }
            
        results.append(result)
        
        # Save intermediate results
        out_file = os.path.join(output_dir, "swebench_results_partial.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    # Save final results
    final_out = os.path.join(output_dir, f"swebench_run_{len(tasks)}.json")
    with open(final_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nBenchmarking complete. Results saved to {final_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archimedes SWE-bench Runner")
    parser.add_argument("--dataset", type=str, required=True, help="Path to SWE-bench JSON file")
    parser.add_argument("--limit", type=int, default=10, help="Max tasks to run")
    parser.add_argument("--outdir", type=str, default="output/benchmarks", help="Output directory")
    
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.dataset, args.limit, args.outdir))
