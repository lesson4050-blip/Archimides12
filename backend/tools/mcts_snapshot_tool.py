import logging
import uuid
import os
from typing import Dict, Any, List
from backend.sandbox.filesystem import SandboxFilesystem

logger = logging.getLogger(__name__)

class MCTSSnapshotTool:
    """
    Monte Carlo Tree Search (MCTS) Snapshot Tool.
    Gives the agent Devin-level trajectory rollback capabilities.
    The agent can take named snapshots of the codebase before risky refactors,
    and rollback to them if tests fail, avoiding infinite error loops.
    """
    
    def __init__(self, filesystem: SandboxFilesystem):
        self.filesystem = filesystem

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "mcts_snapshot",
                "description": (
                    "Manage codebase snapshots for trajectory rollback (MCTS). "
                    "Use this BEFORE attempting risky refactors or dependency changes. "
                    "If your changes break the build, you can rollback to a clean state."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string", 
                            "enum": ["create", "restore", "list"],
                            "description": "The action to perform."
                        },
                        "snapshot_name": {
                            "type": "string",
                            "description": "Name of the snapshot (required for create/restore). E.g., 'pre-refactor'."
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, snapshot_name: str = None, **kwargs) -> Dict[str, Any]:
        # We rely on Git inside the sandbox. We use SandboxFilesystem to run git commands.
        # Ensure the directory is a git repo first.
        
        # Helper to run shell commands in the sandbox via the file system's connection if possible
        # Since SandboxFilesystem doesn't natively expose shell, we will use the shell tool pattern.
        # But for safety, we construct a git branch/tag mechanism.
        
        try:
            from backend.sandbox.manager import get_sandbox_manager
            sandbox = get_sandbox_manager().get_container(session_id)
            if not sandbox:
                return {"success": False, "error": "Sandbox not found for session."}
                
            workdir = "/workspace" # default
            
            # Ensure it's a git repo
            check_git = await sandbox.exec_command(["git", "rev-parse", "--is-inside-work-tree"], workdir=workdir)
            if "true" not in str(check_git.get("output", "")):
                # Initialize git
                await sandbox.exec_command(["git", "init"], workdir=workdir)
                await sandbox.exec_command(["git", "config", "user.name", "Archimedes"], workdir=workdir)
                await sandbox.exec_command(["git", "config", "user.email", "ai@archimedes.dev"], workdir=workdir)
                await sandbox.exec_command(["git", "add", "."], workdir=workdir)
                await sandbox.exec_command(["git", "commit", "-m", "initial state"], workdir=workdir)

            if action == "create":
                if not snapshot_name:
                    snapshot_name = f"snap-{uuid.uuid4().hex[:6]}"
                
                # We use git tags to mark snapshots
                # First, commit all current changes
                await sandbox.exec_command(["git", "add", "."], workdir=workdir)
                await sandbox.exec_command(["git", "commit", "-m", f"Snapshot: {snapshot_name}"], workdir=workdir)
                res = await sandbox.exec_command(["git", "tag", snapshot_name], workdir=workdir)
                
                if res.get("exit_code") != 0:
                    return {"success": False, "error": f"Failed to create snapshot: {res.get('output')}"}
                return {"success": True, "message": f"Snapshot '{snapshot_name}' created successfully."}
                
            elif action == "restore":
                if not snapshot_name:
                    return {"success": False, "error": "snapshot_name is required to restore."}
                    
                # Hard reset to the tag
                res = await sandbox.exec_command(["git", "reset", "--hard", snapshot_name], workdir=workdir)
                await sandbox.exec_command(["git", "clean", "-fd"], workdir=workdir)
                
                if res.get("exit_code") != 0:
                    return {"success": False, "error": f"Failed to restore snapshot: {res.get('output')}"}
                return {"success": True, "message": f"Codebase safely restored to snapshot '{snapshot_name}'."}
                
            elif action == "list":
                res = await sandbox.exec_command(["git", "tag"], workdir=workdir)
                tags = res.get("output", "").strip().split("\n")
                tags = [t for t in tags if t]
                if not tags:
                    return {"success": True, "snapshots": [], "message": "No snapshots found."}
                return {"success": True, "snapshots": tags}
                
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"MCTS Snapshot error: {e}")
            return {"success": False, "error": str(e)}
