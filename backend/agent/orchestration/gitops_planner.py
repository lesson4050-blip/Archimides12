import os
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

class GitOpsPlanner:
    """
    GitOps Planning State (Phase 8).
    Treats PLAN.md as a machine-readable State Machine.
    Supports sleep/wake capabilities via Git commits and Markdown checkboxes.
    """
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.plan_file = os.path.join(workspace_dir, "PLAN.md")

    async def sync_plan(self, completed_index: int = None) -> dict:
        """
        Reads PLAN.md, marks the task at completed_index as [x] if provided, 
        commits to git, and returns the next [ ] task.
        """
        if not os.path.exists(self.plan_file):
            return {"status": "no_plan", "next_task": None, "next_index": None}
            
        try:
            with open(self.plan_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            lines = content.splitlines()
            unchecked_indices = []
            
            for i, line in enumerate(lines):
                if "[ ]" in line:
                    unchecked_indices.append((i, line.replace("[ ]", "").strip()))
            
            marked = False
            if completed_index is not None and unchecked_indices:
                if completed_index < len(unchecked_indices):
                    line_idx, task_text = unchecked_indices[completed_index]
                    lines[line_idx] = lines[line_idx].replace("[ ]", "[x]", 1)
                    marked = True
                    logger.info(f"GitOps Planner marked completed task {completed_index}: {task_text}")
                    
            next_task = None
            next_index = None
            remaining = [(i, l.replace("[ ]", "").strip())
                         for i, l in enumerate(lines) if "[ ]" in l]
            if remaining:
                next_index = 0
                next_task = remaining[0][1]
                    
            if marked:
                with open(self.plan_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                
                await self._git_commit(f"gitops: task {completed_index} completed")

            return {
                "status": "active" if next_task else "complete",
                "next_task": next_task,
                "next_index": next_index,
                "marked_completed": marked,
                "remaining_count": len(remaining)
            }
            
        except Exception as e:
            logger.error(f"GitOpsPlanner failed: {e}")
            return {"status": "error", "error": str(e), "next_task": None}
            
    async def _git_commit(self, message: str):
        safe_message = re.sub(r'[`$\\"\'\n\r;|&><]', '_', message)
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", self.workspace_dir,
                "add", "PLAN.md",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", self.workspace_dir,
                "commit", "-m", safe_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"GitOps commit failed: {stderr.decode()}")
        except Exception as e:
            logger.warning(f"GitOps commit error: {e}")

    async def create_plan(self, plan_content: str):
        """Creates a new PLAN.md and commits it."""
        with open(self.plan_file, "w", encoding="utf-8") as f:
            f.write(plan_content)
        await self._git_commit("gitops: initialized PLAN.md")
