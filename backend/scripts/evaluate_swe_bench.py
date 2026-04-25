import argparse
import asyncio
import json
import logging
import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datasets import load_dataset
from backend.agent.core import ArchimedesCosmoAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("swe-bench-eval")

async def evaluate_instance(agent: ArchimedesCosmoAgent, instance: dict):
    """
    Evaluate Archimedes on a single SWE-bench instance.
    """
    instance_id = instance['instance_id']
    repo = instance['repo']
    base_commit = instance['base_commit']
    problem_statement = instance['problem_statement']
    
    logger.info(f"Evaluating {instance_id} from {repo} at {base_commit}")
    
    # Formulate the prompt for the agent
    prompt = f"""
You are resolving an issue for the repository: {repo}
Base commit: {base_commit}

Issue description:
{problem_statement}

Please analyze the issue, write a patch to resolve it, and return the patch in standard diff format or save it to a file.
    """
    
    # Execute the agent
    # Note: In a real SWE-bench harness, we would launch a sandbox for this specific repo/commit,
    # and pass it to the agent.
    
    result = await agent.run(prompt)
    
    # Extract patch (this would depend on how the agent outputs the patch)
    # For now, we simulate saving the result
    return {
        "instance_id": instance_id,
        "model_patch": result.get("output", ""),
        "model_name_or_path": "Archimedes-CodeAct"
    }

async def main():
    parser = argparse.ArgumentParser(description="Evaluate Archimedes on SWE-bench")
    parser.add_argument("--dataset", type=str, default="princeton-nlp/SWE-bench_Lite", help="Dataset to load")
    parser.add_argument("--limit", type=int, default=10, help="Number of instances to evaluate (0 for all)")
    args = parser.parse_args()

    logger.info(f"Loading dataset {args.dataset}...")
    dataset = load_dataset(args.dataset, split="test")
    
    if args.limit > 0:
        # Select first N instances
        dataset = dataset.select(range(min(args.limit, len(dataset))))
        
    logger.info(f"Loaded {len(dataset)} instances.")
    
    # Initialize the agent
    # We use the CodeAct architecture
    agent = ArchimedesCosmoAgent()
    
    results = []
    
    for i, instance in enumerate(dataset):
        try:
            res = await evaluate_instance(agent, instance)
            results.append(res)
        except Exception as e:
            logger.error(f"Error evaluating instance {instance['instance_id']}: {e}")
            results.append({
                "instance_id": instance['instance_id'],
                "model_patch": "",
                "model_name_or_path": "Archimedes-CodeAct",
                "error": str(e)
            })
            
    # Save results
    os.makedirs("swe_bench_results", exist_ok=True)
    with open("swe_bench_results/predictions.json", "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info("Evaluation complete. Results saved to swe_bench_results/predictions.json")

if __name__ == "__main__":
    asyncio.run(main())
