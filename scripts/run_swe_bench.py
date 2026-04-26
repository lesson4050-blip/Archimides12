#!/usr/bin/env python3
"""
Archimedes SWE-bench Evaluation Script.

Usage:
  python scripts/run_swe_bench.py --instances 10 --split verified
  python scripts/run_swe_bench.py --instance-id django__django-12345

Requires:
  pip install swebench datasets
  GROQ_API_KEY and GOOGLE_API_KEY set in environment
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_evaluation(args):
    """Run SWE-bench evaluation."""
    print(f"🚀 Archimedes SWE-bench Evaluation")
    print(f"   Instances: {args.instances}, Split: {args.split}")
    print(f"   Started: {datetime.now().isoformat()}\n")
    
    # Load SWE-bench dataset
    try:
        from datasets import load_dataset
        dataset = load_dataset(
            "princeton-nlp/SWE-bench_Verified"
            if args.split == "verified"
            else "princeton-nlp/SWE-bench_Lite",
            split="test"
        )
    except ImportError:
        print("ERROR: Run: pip install swebench datasets")
        return
    except Exception as e:
        print(f"ERROR loading dataset: {e}")
        return
    
    # Filter to specific instance if requested
    instances = list(dataset)
    if args.instance_id:
        instances = [i for i in instances if i["instance_id"] == args.instance_id]
        if not instances:
            print(f"Instance {args.instance_id} not found")
            return
    else:
        instances = instances[:args.instances]
    
    print(f"📋 Running {len(instances)} instances...\n")
    
    # Initialize Archimedes agent
    from backend.agent.core import ArchimedesCosmoAgent
    from backend.benchmarks.swe_bench_adapter import SWEBenchAdapter
    
    agent = ArchimedesCosmoAgent(
        name="Archimedes-SWE",
        session_id="swe-bench-eval"
    )
    await asyncio.sleep(2)  # Allow async init to complete
    
    adapter = SWEBenchAdapter(agent)
    
    # Run evaluation
    results = []
    passed = 0
    
    for i, instance in enumerate(instances):
        print(f"[{i+1}/{len(instances)}] {instance['instance_id']}...")
        result = await adapter.run_instance(instance, timeout=args.timeout)
        results.append(result)
        
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = f"{result.get('duration', 0):.1f}s"
        print(f"  {status} | {duration} | {result.get('error', 'OK')[:60]}")
        
        if result["success"]:
            passed += 1
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "split": args.split,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results) * 100, 1) if results else 0,
        "results": results
    }
    
    output_path = f"swe_bench_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"   Passed: {passed}/{len(results)} ({output['pass_rate']}%)")
    print(f"   Results saved: {output_path}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="Archimedes SWE-bench Evaluation")
    parser.add_argument("--instances", type=int, default=10,
                       help="Number of instances to evaluate")
    parser.add_argument("--split", choices=["verified", "lite"], default="verified",
                       help="SWE-bench split to use")
    parser.add_argument("--instance-id", type=str, default=None,
                       help="Run a specific instance by ID")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout per instance in seconds")
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(args))


if __name__ == "__main__":
    main()
