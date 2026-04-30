import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum

class SecurityCheckID(IntEnum):
    PERMISSION_REQUIRED = 19
    DANGEROUS_PATTERNS = 4

@dataclass
class SecurityResult:
    allowed: bool
    check_id: Optional[SecurityCheckID] = None
    message: str = \"\"
    severity: str = \"blocked\"

PERMISSION_REQUIRED_COMMANDS = {\"rm -rf\", \"chmod\", \"kill\"}
ALWAYS_BLOCKED = {\"rm -rf /\", \"mkfs\", \"dd if=/dev/zero\"}

def validate_command(command: str) -> SecurityResult:
    cmd_lower = command.strip().lower()
    for blocked in ALWAYS_BLOCKED:
        if blocked in cmd_lower:
            is_perm = any(perm in blocked for perm in PERMISSION_REQUIRED_COMMANDS)
            return SecurityResult(False, SecurityCheckID.DANGEROUS_PATTERNS, f\"Blocked: {blocked}\", \"permission_required\" if is_perm else \"blocked\")
    return SecurityResult(True, message=\"OK\")
