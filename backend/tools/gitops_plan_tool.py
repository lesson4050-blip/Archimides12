"""
Phase 8 — Shift 3: GitOps Planning State Machine (OpenHands-killer).
PLAN.md becomes a persistent, machine-readable execution state.
If the system crashes, it resumes from the last unchecked [ ] item.
Enables sleep/wake infinite session persistence.
"""
import os
import re
import base64
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GitOpsPlanTool:
    """
    Manages a PLAN.md file as a machine-readable state machine.
    The agent creates plans with [ ] checkboxes, executes them step-by-step,
    marks completed items [x], and commits each checkpoint to Git.
    On restart, resumes from the first unchecked [ ] item.
    """

    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "gitops_plan",
                "description": (
                    "PERSISTENCE ENGINE: Create and manage a PLAN.md execution state machine. "
                    "Actions: "
                    "'create' — write a new plan with [ ] checkboxes. "
                    "'next' — get the next unchecked task from the plan. "
                    "'complete' — mark a specific task as [x] done and git commit. "
                    "'status' — show plan progress summary. "
                    "Use this for complex multi-step projects so progress is never lost."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "next", "complete", "status"],
                            "description": "The plan operation to perform."
                        },
                        "plan_content": {
                            "type": "string",
                            "description": "For 'create': full markdown plan with [ ] checkboxes."
                        },
                        "task_text": {
                            "type": "string",
                            "description": "For 'complete': the text of the task to mark as done."
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, session_id: str, action: str,
                      plan_content: str = "", task_text: str = "", **kwargs) -> Dict[str, Any]:
        from backend.sandbox.singleton import sandbox_manager

        plan_path = "/workspace/PLAN.md"

        if action == "create":
            if not plan_content:
                return {"success": False, "error": "plan_content is required for 'create' action."}

            b64 = base64.b64encode(plan_content.encode("utf-8")).decode("utf-8")
            cmd = (
                f"echo '{b64}' | base64 -d > {plan_path} && "
                f"cd /workspace && git add PLAN.md && "
                f"git commit -m 'gitops: initialized PLAN.md' --allow-empty 2>&1"
            )
            result = await sandbox_manager.executor.run_command(
                session_id=session_id, command=cmd, timeout=15
            )
            return {
                "success": True,
                "output": f"PLAN.md created with {plan_content.count('[ ]')} tasks. Git committed."
            }

        elif action == "next":
            cmd = f"cat {plan_path} 2>/dev/null || echo '__NO_PLAN__'"
            result = await sandbox_manager.executor.run_command(
                session_id=session_id, command=cmd, timeout=5
            )
            content = result.get("output", "")
            if "__NO_PLAN__" in content:
                return {"success": False, "error": "No PLAN.md found. Create one first."}

            # Find first unchecked task
            for line in content.splitlines():
                match = re.search(r'\[ \]\s*(.+)', line)
                if match:
                    next_task = match.group(1).strip()
                    total = content.count("[ ]") + content.count("[x]")
                    done = content.count("[x]")
                    return {
                        "success": True,
                        "output": next_task,
                        "progress": f"{done}/{total} completed"
                    }

            return {"success": True, "output": "ALL TASKS COMPLETE ✅", "progress": "100%"}

        elif action == "complete":
            if not task_text:
                return {"success": False, "error": "task_text is required for 'complete' action."}

            # Read, mark, write, commit
            cmd = f"cat {plan_path}"
            result = await sandbox_manager.executor.run_command(
                session_id=session_id, command=cmd, timeout=5
            )
            content = result.get("output", "")
            if not content:
                return {"success": False, "error": "Cannot read PLAN.md."}

            # Find and mark the matching task
            lines = content.splitlines()
            marked = False
            for i, line in enumerate(lines):
                if "[ ]" in line and task_text.lower()[:30] in line.lower():
                    lines[i] = line.replace("[ ]", "[x]", 1)
                    marked = True
                    break

            if not marked:
                return {"success": False, "error": f"Task not found in PLAN.md: '{task_text[:50]}'"}

            new_content = "\n".join(lines)
            b64 = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
            safe_msg = task_text[:40].replace("'", "").replace('"', '')
            cmd = (
                f"echo '{b64}' | base64 -d > {plan_path} && "
                f"cd /workspace && git add PLAN.md && "
                f"git commit -m 'gitops: completed — {safe_msg}' 2>&1"
            )
            result = await sandbox_manager.executor.run_command(
                session_id=session_id, command=cmd, timeout=15
            )
            return {
                "success": True,
                "output": f"✅ Marked as done: {task_text[:60]}. Committed to Git."
            }

        elif action == "status":
            cmd = f"cat {plan_path} 2>/dev/null || echo '__NO_PLAN__'"
            result = await sandbox_manager.executor.run_command(
                session_id=session_id, command=cmd, timeout=5
            )
            content = result.get("output", "")
            if "__NO_PLAN__" in content:
                return {"success": False, "error": "No PLAN.md found."}

            total = content.count("[ ]") + content.count("[x]")
            done = content.count("[x]")
            remaining = content.count("[ ]")
            pct = round((done / total * 100) if total > 0 else 0)

            return {
                "success": True,
                "output": f"Plan Progress: {done}/{total} tasks ({pct}%)\n"
                          f"Remaining: {remaining} tasks",
                "plan_text": content[:3000]
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}. Use create/next/complete/status."}
