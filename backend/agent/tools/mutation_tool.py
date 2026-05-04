import logging
import asyncio
import os
import ast
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MutationTool:
    """
    Self-Healing TDD Tool: Mutation Testing.
    Deliberately breaks code to ensure tests catch the failure.
    If a test passes despite broken code, the test is weak and needs rewriting.
    """
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "mutate_test",
            "description": "Mutate (break) a python file to verify test suite strength. If tests pass after mutation, the tests are weak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["mutate", "restore"]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the python file to mutate"
                    },
                    "test_command": {
                        "type": "string",
                        "description": "The pytest command to run (e.g. 'pytest tests/test_file.py')"
                    }
                },
                "required": ["action", "file_path"]
            }
        }

    async def execute(self, action: str, file_path: str, **kwargs) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        backup_path = file_path + ".mutbak"

        try:
            if action == "restore":
                if os.path.exists(backup_path):
                    with open(backup_path, "r", encoding="utf-8") as f:
                        original = f.read()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(original)
                    os.remove(backup_path)
                    return {"success": True, "output": "File restored from backup."}
                return {"success": False, "error": "No backup found to restore."}

            elif action == "mutate":
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                # Backup
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(source)

                # Simple mutation strategy: flip comparison operators
                # == to !=, > to <, < to >, >= to <=, <= to >=
                mutations = [
                    ("==", "!="),
                    ("!=", "=="),
                    (" > ", " < "),
                    (" < ", " > "),
                    (" >= ", " <= "),
                    (" <= ", " >= "),
                    ("True", "False"),
                    ("False", "True"),
                    (" and ", " or "),
                    (" or ", " and ")
                ]

                mutated_source = source
                mutation_applied = None

                # Find a random valid mutation
                random.shuffle(mutations)
                for old, new in mutations:
                    if old in mutated_source:
                        # Replace only the first occurrence to isolate the mutation
                        mutated_source = mutated_source.replace(old, new, 1)
                        mutation_applied = f"Changed '{old.strip()}' to '{new.strip()}'"
                        break

                if not mutation_applied:
                    os.remove(backup_path)
                    return {"success": False, "error": "Could not find a suitable mutation target in the file."}

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(mutated_source)

                test_cmd = kwargs.get("test_command")
                test_results = "No test command provided."

                if test_cmd:
                    process = await asyncio.create_subprocess_shell(
                        test_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    rc = process.returncode
                    
                    if rc == 0:
                        test_results = (
                            f"WARNING: Tests PASSED despite mutation! "
                            f"The test suite is WEAK and did not catch the injected bug ({mutation_applied}).\n"
                            f"Output: {stdout.decode()[:500]}"
                        )
                    else:
                        test_results = (
                            f"SUCCESS: Tests FAILED as expected. "
                            f"The test suite is STRONG and caught the injected bug ({mutation_applied}).\n"
                            f"Output: {stdout.decode()[:500]}"
                        )

                return {
                    "success": True,
                    "mutation_applied": mutation_applied,
                    "test_results": test_results,
                    "instruction": "If tests PASSED, rewrite the tests to be stricter. ALWAYS run 'restore' action afterwards."
                }

        except Exception as e:
            logger.error(f"MutationTool execution failed: {e}")
            if os.path.exists(backup_path):
                # Auto-restore on crash
                with open(backup_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(original)
                os.remove(backup_path)
            return {"success": False, "error": str(e)}
