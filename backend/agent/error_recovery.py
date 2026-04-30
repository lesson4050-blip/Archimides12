"""
Error Recovery v2: Git-aware checkpointing + structured error classification.

Key upgrades over v1:
- Git snapshot before risky operations (auto-rollback on failure)
- Error classification by type for targeted recovery strategies
- Exponential backoff with jitter for transient failures
- Kill-switch: abort after N consecutive failures on same file/tool
"""
import asyncio
import hashlib
import logging
import datetime
import subprocess
import os
import re
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    DEPENDENCY = "dependency"
    NETWORK = "network"
    TOOL_MISUSE = "tool_misuse"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    tool_name: str
    params_hash: str
    error: str
    error_type: ErrorType
    timestamp: str
    file_path: Optional[str] = None
    git_checkpoint: Optional[str] = None


class ErrorRecovery:
    """
    v2: Git-aware error recovery with structured classification.
    
    Handles:
    1. Auto-checkpointing before risky edits
    2. Automatic rollback on cascading failures
    3. Typed recovery advice based on error classification
    4. Exponential backoff for transient errors
    5. Kill-switch to prevent infinite retry loops
    """

    MAX_RETRIES = 3
    MAX_CONSECUTIVE_FAILURES = 5  # Kill-switch threshold
    CHECKPOINT_PREFIX = "archimedes-checkpoint"

    def __init__(self, workspace_dir: Optional[str] = None):
        self.tool_failure_history: List[FailureRecord] = []
        self.consecutive_failures: int = 0
        self.workspace_dir = workspace_dir
        self._checkpoints: Dict[str, str] = {}  # session_id -> commit SHA

    # ─── Error Classification ─────────────────────────────────────

    @staticmethod
    def classify_error(error: str) -> ErrorType:
        """Classify an error string into a structured type."""
        err_lower = error.lower()

        if any(kw in err_lower for kw in ["syntaxerror", "indentationerror", "invalid syntax"]):
            return ErrorType.SYNTAX
        if any(kw in err_lower for kw in ["timeout", "timed out", "deadline exceeded"]):
            return ErrorType.TIMEOUT
        if any(kw in err_lower for kw in ["permission denied", "access denied", "eacces"]):
            return ErrorType.PERMISSION
        if any(kw in err_lower for kw in [
            "not found", "no such file", "modulenotfounderror",
            "command not found", "filenotfounderror"
        ]):
            return ErrorType.NOT_FOUND
        if any(kw in err_lower for kw in [
            "modulenotfounderror", "importerror", "no module named",
            "package not found", "pip install"
        ]):
            return ErrorType.DEPENDENCY
        if any(kw in err_lower for kw in [
            "connectionerror", "urlerror", "network", "dns",
            "refused", "unreachable"
        ]):
            return ErrorType.NETWORK
        if any(kw in err_lower for kw in [
            "missing required", "invalid parameter", "expected",
            "required field", "type error"
        ]):
            return ErrorType.TOOL_MISUSE
        if any(kw in err_lower for kw in [
            "runtimeerror", "exception", "error", "traceback",
            "failed", "assertion"
        ]):
            return ErrorType.RUNTIME

        return ErrorType.UNKNOWN

    # ─── Failure Recording ────────────────────────────────────────

    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Create a stable hash of tool parameters for deduplication."""
        raw = str(sorted(params.items()))
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def record_failure(
        self,
        tool_name: str,
        params: Dict[str, Any],
        error: str,
        file_path: Optional[str] = None
    ):
        """Record a tool failure with classification."""
        error_type = self.classify_error(error)
        record = FailureRecord(
            tool_name=tool_name,
            params_hash=self._hash_params(params),
            error=error[:500],
            error_type=error_type,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            file_path=file_path,
            git_checkpoint=self._checkpoints.get("current")
        )
        self.tool_failure_history.append(record)
        self.consecutive_failures += 1

        logger.warning(
            f"[ErrorRecovery] Failure #{self.consecutive_failures}: "
            f"{tool_name} -> {error_type.value} | {error[:100]}"
        )

    def record_success(self):
        """Reset consecutive failure counter on success."""
        self.consecutive_failures = 0

    # ─── Retry Logic ──────────────────────────────────────────────

    def should_retry(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """Check if we should retry this exact tool call."""
        # Kill-switch: abort after too many consecutive failures
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            logger.error(
                f"[ErrorRecovery] KILL SWITCH: {self.consecutive_failures} "
                f"consecutive failures. Aborting retries."
            )
            return False

        params_hash = self._hash_params(params)
        same_failures = [
            f for f in self.tool_failure_history
            if f.tool_name == tool_name and f.params_hash == params_hash
        ]
        return len(same_failures) < self.MAX_RETRIES

    async def backoff_delay(self, retry_count: int):
        """Exponential backoff with jitter for transient errors."""
        base_delay = min(2 ** retry_count, 16)  # Cap at 16s
        jitter = random.uniform(0, base_delay * 0.3)
        delay = base_delay + jitter
        logger.info(f"[ErrorRecovery] Backoff: {delay:.1f}s before retry #{retry_count + 1}")
        await asyncio.sleep(delay)

    # ─── Recovery Advice ──────────────────────────────────────────

    def get_recovery_advice(self, tool_name: str, error: str) -> str:
        """Get specific recovery advice based on error classification."""
        error_type = self.classify_error(error)

        strategies = {
            ErrorType.SYNTAX: (
                "SYNTAX ERROR detected. "
                "1. Re-read the file to get accurate line numbers. "
                "2. Fix the specific line causing the error. "
                "3. Use the fast_linter tool to validate before committing."
            ),
            ErrorType.TIMEOUT: (
                "TIMEOUT. The operation took too long. Options: "
                "1. Break the command into smaller parts. "
                "2. Add a longer timeout parameter. "
                "3. Check if the process is stuck in an infinite loop."
            ),
            ErrorType.PERMISSION: (
                "PERMISSION DENIED. Options: "
                "1. Check file ownership with 'ls -la'. "
                "2. Use 'chmod' to fix permissions. "
                "3. Ensure you're operating within the sandbox."
            ),
            ErrorType.NOT_FOUND: (
                "NOT FOUND. The file, command, or path doesn't exist. "
                "1. Use 'find' or 'ls' to locate the correct path. "
                "2. Check for typos in the path/command. "
                "3. The file may need to be created first."
            ),
            ErrorType.DEPENDENCY: (
                "MISSING DEPENDENCY. "
                "1. Install it: pip install <package> or npm install <package>. "
                "2. Check the import statement for typos. "
                "3. Verify you're using the correct package name."
            ),
            ErrorType.NETWORK: (
                "NETWORK ERROR. "
                "1. Check if the URL is correct. "
                "2. The service may be down — try an alternative source. "
                "3. Check sandbox network permissions."
            ),
            ErrorType.TOOL_MISUSE: (
                "TOOL MISUSE: wrong parameters passed. "
                "1. Review the tool's required parameters. "
                "2. Ensure parameter types are correct (string vs int). "
                "3. Check if you're using the right action for this tool."
            ),
            ErrorType.RUNTIME: (
                "RUNTIME ERROR in execution. "
                "1. Read the full traceback to find the root cause. "
                "2. Check variable types and None values. "
                "3. Add try/except around the failing section."
            ),
            ErrorType.UNKNOWN: (
                f"UNKNOWN ERROR: {error[:200]}. "
                "1. Try a completely different approach. "
                "2. Read the file to understand current state. "
                "3. Check system logs for more details."
            )
        }

        advice = strategies.get(error_type, strategies[ErrorType.UNKNOWN])

        # Add context from similar past failures
        similar = [
            f for f in self.tool_failure_history
            if f.error_type == error_type and f.tool_name == tool_name
        ]
        if len(similar) > 1:
            advice += (
                f"\n⚠️ This is failure #{len(similar)} of type '{error_type.value}' "
                f"for tool '{tool_name}'. Consider switching strategy entirely."
            )

        return advice

    # ─── Git Checkpointing ────────────────────────────────────────

    def create_checkpoint(self, session_id: str, label: str = "") -> Optional[str]:
        """
        Create a git checkpoint before risky operations.
        Returns the commit SHA or None if git isn't available.
        """
        if not self.workspace_dir or not os.path.isdir(self.workspace_dir):
            return None

        try:
            # Check if workspace is a git repo
            check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.workspace_dir,
                capture_output=True, text=True, timeout=5
            )
            if check.returncode != 0:
                return None

            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.workspace_dir,
                capture_output=True, timeout=10
            )

            # Commit checkpoint
            msg = f"{self.CHECKPOINT_PREFIX}: {label or session_id} @ {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
            result = subprocess.run(
                ["git", "commit", "-m", msg, "--allow-empty"],
                cwd=self.workspace_dir,
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                # Get the SHA
                sha_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.workspace_dir,
                    capture_output=True, text=True, timeout=5
                )
                sha = sha_result.stdout.strip()
                self._checkpoints[session_id] = sha
                self._checkpoints["current"] = sha
                logger.info(f"[ErrorRecovery] Checkpoint created: {sha[:8]} ({label})")
                return sha

        except Exception as e:
            logger.warning(f"[ErrorRecovery] Checkpoint failed: {e}")

        return None

    def rollback_to_checkpoint(self, session_id: str) -> bool:
        """
        Rollback workspace to the last checkpoint for this session.
        Returns True if rollback succeeded.
        """
        sha = self._checkpoints.get(session_id)
        if not sha or not self.workspace_dir:
            logger.warning("[ErrorRecovery] No checkpoint to rollback to.")
            return False

        try:
            result = subprocess.run(
                ["git", "reset", "--hard", sha],
                cwd=self.workspace_dir,
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"[ErrorRecovery] Rolled back to {sha[:8]}")
                self.consecutive_failures = 0  # Reset after rollback
                return True
            else:
                logger.error(f"[ErrorRecovery] Rollback failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"[ErrorRecovery] Rollback exception: {e}")
            return False

    # ─── Diagnostics ──────────────────────────────────────────────

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get a summary of all failures for debugging."""
        by_type = {}
        for f in self.tool_failure_history:
            key = f.error_type.value
            by_type[key] = by_type.get(key, 0) + 1

        by_tool = {}
        for f in self.tool_failure_history:
            by_tool[f.tool_name] = by_tool.get(f.tool_name, 0) + 1

        return {
            "total_failures": len(self.tool_failure_history),
            "consecutive_failures": self.consecutive_failures,
            "kill_switch_triggered": self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES,
            "failures_by_type": by_type,
            "failures_by_tool": by_tool,
            "checkpoints": {k: v[:8] for k, v in self._checkpoints.items()},
            "recent_errors": [
                {
                    "tool": f.tool_name,
                    "type": f.error_type.value,
                    "error": f.error[:100],
                    "time": f.timestamp
                }
                for f in self.tool_failure_history[-5:]
            ]
        }

    def should_escalate(self) -> Tuple[bool, str]:
        """
        Check if the situation requires escalation (human or strategy change).
        Returns (should_escalate, reason).
        """
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            return True, (
                f"Kill switch: {self.consecutive_failures} consecutive failures. "
                f"Last error types: "
                + ", ".join(
                    f.error_type.value
                    for f in self.tool_failure_history[-3:]
                )
            )

        # Check for oscillation (same error type repeating)
        if len(self.tool_failure_history) >= 4:
            last4_types = [f.error_type for f in self.tool_failure_history[-4:]]
            if len(set(last4_types)) == 1:
                return True, (
                    f"Oscillation detected: same error type "
                    f"'{last4_types[0].value}' repeated 4 times."
                )

        return False, ""

    # ── JSON Resilient Parsing (small model fallback) ────────────

    @staticmethod
    def extract_json_resilient(text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM output that may contain markdown fences,
        trailing commas, or other formatting artifacts.

        Handles:
        - ```json ... ``` blocks
        - Leading/trailing prose around JSON
        - Trailing commas before } or ]
        - Single quotes instead of double quotes
        - Missing closing brackets
        """
        import json

        if not text or not text.strip():
            return None

        # Step 1: Extract from markdown code fences
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Step 2: Find JSON-like boundaries
        start = -1
        for i, c in enumerate(text):
            if c in ('{', '['):
                start = i
                break

        if start == -1:
            return None

        # Find matching closing bracket
        opener = text[start]
        closer = '}' if opener == '{' else ']'
        depth = 0
        end = -1
        in_str = False
        escape = False

        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\' and in_str:
                escape = True
                continue
            if c == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end == -1:
            # Try auto-closing
            candidate = text[start:] + closer * depth
        else:
            candidate = text[start:end]

        # Step 3: Fix common issues
        # Trailing commas
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        # Single quotes to double quotes (rough)
        if "'" in candidate and '"' not in candidate:
            candidate = candidate.replace("'", '"')

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Step 4: Last resort — use json_repair if available
        try:
            from backend.utils.json_repair import repair_and_parse
            result, _ = repair_and_parse(candidate)
            return result
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")

        return None

    # ── Self-Healing Loop Detection ──────────────────────────────

    def self_healing_check(self) -> Dict[str, Any]:
        """
        Analyze failure history for stuck patterns and suggest remediation.

        Returns:
            {
                "stuck": bool,
                "pattern": str,  # Description of detected pattern
                "suggestion": str,  # Remediation action
                "severity": str,  # "low", "medium", "high", "critical"
            }
        """
        if len(self.tool_failure_history) < 3:
            return {"stuck": False, "pattern": "", "suggestion": "", "severity": "low"}

        recent = self.tool_failure_history[-6:]

        # Pattern 1: Same file being modified repeatedly with errors (Most Specific)
        file_paths = [f.file_path for f in recent if f.file_path]
        if file_paths:
            most_common_file = max(set(file_paths), key=file_paths.count)
            file_freq = file_paths.count(most_common_file)
            if file_freq >= 2:
                return {
                    "stuck": True,
                    "pattern": f"File '{most_common_file}' causing repeated failures ({file_freq}x)",
                    "suggestion": f"Read '{most_common_file}' fully before attempting changes, or rollback to checkpoint",
                    "severity": "medium",
                }

        # Pattern 2: Same tool failing repeatedly
        tool_names = [f.tool_name for f in recent]
        most_common_tool = max(set(tool_names), key=tool_names.count)
        tool_freq = tool_names.count(most_common_tool)
        if tool_freq >= 3:
            return {
                "stuck": True,
                "pattern": f"Tool '{most_common_tool}' failed {tool_freq}/{len(recent)} times",
                "suggestion": f"Exclude '{most_common_tool}' and try alternative tools",
                "severity": "high",
            }

        # Pattern 3: Same error type oscillating
        error_types = [f.error_type for f in recent]
        most_common_type = max(set(error_types), key=error_types.count)
        type_freq = error_types.count(most_common_type)
        if type_freq >= 4:
            return {
                "stuck": True,
                "pattern": f"Error type '{most_common_type.value}' repeating ({type_freq}x)",
                "suggestion": "Change strategy entirely — current approach is fundamentally wrong",
                "severity": "critical",
            }

        # Pattern 4: Rapid failures (all within short timeframe)
        if len(recent) >= 4:
            timestamps = []
            for f in recent:
                try:
                    ts = datetime.datetime.fromisoformat(f.timestamp.replace("Z", "+00:00"))
                    timestamps.append(ts)
                except (ValueError, AttributeError):
                    pass
            if len(timestamps) >= 4:
                time_span = (timestamps[-1] - timestamps[0]).total_seconds()
                if time_span < 30:  # 4+ failures in 30 seconds
                    return {
                        "stuck": True,
                        "pattern": f"{len(timestamps)} failures in {time_span:.0f}s — thrashing",
                        "suggestion": "Pause and re-read the task description before continuing",
                        "severity": "high",
                    }

        return {"stuck": False, "pattern": "", "suggestion": "", "severity": "low"}

