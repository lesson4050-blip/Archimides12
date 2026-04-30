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
    \"\"\"
    v2: Git-aware error recovery with structured classification.
    \"\"\"
    def __init__(self, workspace_dir: str = \".\"):
        self.workspace_dir = workspace_dir
        self.tool_failure_history: List[FailureRecord] = []
        self.consecutive_failures = 0
        self.MAX_CONSECUTIVE_FAILURES = 5
        self._checkpoints: Dict[str, str] = {}

    def record_failure(self, tool_name: str, params: Dict[str, Any], error: str, file_path: Optional[str] = None):
        error_type = self._classify_error(error)
        params_hash = hashlib.md5(str(params).encode()).hexdigest()
        record = FailureRecord(
            tool_name=tool_name,
            params_hash=params_hash,
            error=error,
            error_type=error_type,
            timestamp=datetime.datetime.now().isoformat(),
            file_path=file_path
        )
        self.tool_failure_history.append(record)
        self.consecutive_failures += 1
        logger.warning(f\"[ErrorRecovery] Failure #{self.consecutive_failures}: {tool_name} -> {error_type.value} | {error[:100]}\")

    def reset_failures(self):
        self.consecutive_failures = 0

    def _classify_error(self, error: str) -> ErrorType:
        error_lower = error.lower()
        if \"syntaxerror\" in error_lower or \"invalid syntax\" in error_lower:
            return ErrorType.SYNTAX
        if \"timeout\" in error_lower or \"timed out\" in error_lower:
            return ErrorType.TIMEOUT
        if \"permission denied\" in error_lower or \"eacces\" in error_lower:
            return ErrorType.PERMISSION
        if \"not found\" in error_lower or \"enoent\" in error_lower:
            return ErrorType.NOT_FOUND
        if \"module not found\" in error_lower or \"importball\" in error_lower:
            return ErrorType.DEPENDENCY
        if \"connection\" in error_lower or \"network\" in error_lower:
            return ErrorType.NETWORK
        return ErrorType.RUNTIME

    def should_escalate(self) -> Tuple[bool, str]:
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            return True, f\"Kill switch: {self.consecutive_failures} consecutive failures.\"
        return False, \"\"

    @staticmethod
    def extract_json_resilient(text: str) -> Optional[Dict]:
        import json
        if not text or not text.strip(): return None
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
        if fence_match: text = fence_match.group(1).strip()
        start = -1
        for i, c in enumerate(text):
            if c in ('{', '['):
                start = i
                break
        if start == -1: return None
        opener = text[start]
        closer = '}' if opener == '{' else ']'
        depth, end, in_str, escape = 0, -1, False, False
        for i in range(start, len(text)):
            c = text[i]
            if escape: {escape := False; continue}
            if c == '\\\\' and in_str: {escape := True; continue}
            if c == '\"' and not escape: {in_str := not in_str; continue}
            if in_str: continue
            if c == opener: depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0: {end := i + 1; break}
        candidate = text[start:end] if end != -1 else text[start:] + closer * depth
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try: return json.loads(candidate)
        except: pass
        return None

    def self_healing_check(self) -> Dict[str, Any]:
        if len(self.tool_failure_history) < 2: return {\"stuck\": False}
        recent = self.tool_failure_history[-6:]
        file_paths = [f.file_path for f in recent if f.file_path]
        if file_paths:
            most_common_file = max(set(file_paths), key=file_paths.count)
            if file_paths.count(most_common_file) >= 2:
                return {\"stuck\": True, \"pattern\": f\"File '{most_common_file}' errors\", \"suggestion\": \"Read file fully\", \"severity\": \"medium\"}
        return {\"stuck\": False}
