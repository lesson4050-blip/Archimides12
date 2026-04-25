"""
SWE-bench Adapter — run Archimedes on SWE-bench style tasks.
Translates SWE-bench instance format to Archimedes task format.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SWEBenchAdapter:
    """
    Adapter to run Archimedes on SWE-bench evaluation tasks.
    
    SWE-bench task format:
    {
        "instance_id": "django__django-12345",
        "repo": "django/django",
        "base_commit": "abc123",
        "problem_statement": "Bug description...",
        "hints_text": "Optional hints...",
        "test_patch": "Test file diff...",
        "patch": "Expected solution patch..."
    }
    """
    
    def __init__(self, agent):
        self.agent = agent
    
    async def run_instance(
        self,
        instance: Dict[str, Any],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Run a single SWE-bench instance through Archimedes."""
        instance_id = instance.get("instance_id", "unknown")
        problem = instance.get("problem_statement", "")
        repo = instance.get("repo", "")
        hints = instance.get("hints_text", "")
        
        # Format as Archimedes task
        task = f"""SWE-bench task: {instance_id}
Repository: {repo}
Problem: {problem}
{f"Hints: {hints}" if hints else ""}

Instructions:
1. Use repo_map tool to understand the codebase structure
2. Use ast_navigator to find relevant code
3. Write a minimal patch using the patch tool
4. Run the existing tests to verify the fix
5. Output the final unified diff patch"""
        
        try:
            result = await asyncio.wait_for(
                self.agent.process_task(task, mode="planning"),
                timeout=timeout
            )
            return {
                "instance_id": instance_id,
                "success": result.status.value == "completed",
                "output": str(result.output or ""),
                "error": result.error,
                "duration": result.duration,
            }
        except asyncio.TimeoutError:
            return {
                "instance_id": instance_id,
                "success": False,
                "output": "",
                "error": f"Timeout after {timeout}s",
                "duration": timeout,
            }
        except Exception as e:
            return {
                "instance_id": instance_id,
                "success": False,
                "output": "",
                "error": str(e),
                "duration": 0,
            }
    
    async def run_batch(
        self,
        instances: list,
        max_concurrent: int = 3
    ) -> list:
        """Run multiple SWE-bench instances with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(instance):
            async with semaphore:
                return await self.run_instance(instance)
        
        tasks = [run_with_semaphore(inst) for inst in instances]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            r if isinstance(r, dict) else {"error": str(r), "success": False}
            for r in results
        ]
