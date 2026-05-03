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

    async def sync_plan(self, completed_task: str = None) -> dict:
        """
        Reads PLAN.md, marks completed_task as [x] if provided, 
        commits to git, and returns the next [ ] task.
        """
        if not os.path.exists(self.plan_file):
            return {"status": "no_plan", "next_task": None}
            
        try:
            with open(self.plan_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            lines = content.splitlines()
            updated_lines = []
            next_task = None
            marked = False
            
            for line in lines:
                # If a task was completed, we search for it and mark it [x]
                if completed_task and not marked and "[ ]" in line:
                    clean_line = line.replace("[ ]", "").strip()
                    # A naive subset match for the completed task text
                    if clean_line[:20].lower() in completed_task.lower() or completed_task.lower() in clean_line[:20].lower():
                        line = line.replace("[ ]", "[x]", 1)
                        marked = True
                        logger.info(f"GitOps Planner marked completed: {clean_line}")
                        
                updated_lines.append(line)
                
                # Find the NEXT unchecked task
                if next_task is None and "[ ]" in line:
                    next_task = line.replace("[ ]", "").strip()
                    
            if marked:
                with open(self.plan_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(updated_lines))
                
                # Commit to Git to preserve state
                await self._git_commit(f"gitops: completed task '{completed_task[:30]}'")

            return {
                "status": "active" if next_task else "complete",
                "next_task": next_task,
                "marked_completed": marked
            }
            
        except Exception as e:
            logger.error(f"GitOpsPlanner failed: {e}")
            return {"status": "error", "error": str(e), "next_task": None}
            
    async def _git_commit(self, message: str):
        try:
            proc = await asyncio.create_subprocess_shell(
                f'cd "{self.workspace_dir}" && git add PLAN.md && git commit -m "{message}"',
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
