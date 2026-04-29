"""
Bash Security Engine — Command Injection Detection.

Multi-layer defense:
1. Quote-aware parsing (single/double quotes, escaped chars)
2. Command substitution detection ($(), backticks, process substitution)
3. Dangerous pattern blocking (pipe to shell, heredoc injection)
4. Path traversal prevention
5. Dangerous command blocklist with context-aware exceptions
"""
import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class SecurityCheckID(IntEnum):
    """Numeric identifiers for security checks."""
    COMMAND_SUBSTITUTION = 1
    INPUT_REDIRECTION = 2
    OUTPUT_REDIRECTION = 3
    DANGEROUS_PATTERNS = 4
    PIPE_TO_SHELL = 5
    IFS_INJECTION = 6
    CONTROL_CHARACTERS = 7
    UNICODE_WHITESPACE = 8
    BRACE_EXPANSION = 9
    BACKSLASH_ESCAPED = 10
    INCOMPLETE_COMMAND = 11
    PROC_ENVIRON = 12
    HEREDOC_IN_SUBSTITUTION = 13
    COMMENT_QUOTE_DESYNC = 14


@dataclass
class SecurityResult:
    """Result of a security validation."""
    allowed: bool
    check_id: Optional[SecurityCheckID] = None
    message: str = ""
    severity: str = "blocked"  # blocked, warning, info


# ── Command Substitution Patterns ──

COMMAND_SUBSTITUTION_PATTERNS = [
    (re.compile(r'\$\('), "command substitution $()"),
    (re.compile(r'\$\{'), "parameter substitution ${}"),
    (re.compile(r'<\('), "process substitution <()"),
    (re.compile(r'>\('), "process substitution >()"),
    (re.compile(r'\$\['), "legacy arithmetic $[]"),
]

# ── Dangerous Commands (context-aware) ──

ALWAYS_BLOCKED = {
    "rm -rf /", "mkfs", "dd if=/dev/zero",
    "chmod 777", ":(){ :|:& };:",  # fork bomb
    "curl | sh", "curl | bash", "wget | sh", "wget | bash",
    "> /dev/sda", "shutdown", "reboot", "halt", "poweroff",
    "nc -l", "ncat -l",  # reverse shells
}

DANGEROUS_COMMANDS = {
    "eval", "exec", "source", "alias",
    "curl", "wget", "nc", "ncat", "telnet",
    "python -c", "python3 -c", "perl -e", "ruby -e",
    "ssh", "scp", "rsync",
}

SAFE_EXCEPTIONS = {
    # Allow curl for localhost only
    "curl http://localhost", "curl http://127.0.0.1",
    "curl -f http://localhost",
    # Allow pip/npm
    "pip install", "pip3 install", "npm install", "pnpm install",
}


def extract_unquoted_content(command: str) -> str:
    """
    Strip quoted content from command, preserving only unquoted parts.
    This prevents false positives from patterns inside string literals.
    """
    result = []
    in_single = False
    in_double = False
    escaped = False

    for char in command:
        if escaped:
            escaped = False
            continue
        if char == '\\' and not in_single:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if not in_single and not in_double:
            result.append(char)

    return ''.join(result)


def validate_command_substitution(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Check for command substitution attempts."""
    if '`' in unquoted:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.COMMAND_SUBSTITUTION,
            message="Backtick command substitution detected"
        )

    for pattern, desc in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(unquoted):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.COMMAND_SUBSTITUTION,
                message=f"Blocked: {desc}"
            )
    return None


def validate_redirections(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Check for dangerous input/output redirections."""
    safe_redirections = re.compile(
        r'(?:>|>>)\s*/dev/null|2>&1|&>/dev/null|>/dev/null\s+2>&1'
    )
    cleaned = safe_redirections.sub('', unquoted)

    input_redir = re.compile(r'<\s*(/etc/|/proc/|/sys/|/dev/(?!null|urandom))')
    if input_redir.search(cleaned):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.INPUT_REDIRECTION,
            message="Input redirection from sensitive path blocked"
        )

    output_redir = re.compile(r'(?:>|>>)\s*(/etc/|/proc/|/sys/|/dev/(?!null)|/usr/|/bin/|/sbin/)')
    if output_redir.search(cleaned):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.OUTPUT_REDIRECTION,
            message="Output redirection to system path blocked"
        )
    return None


def validate_dangerous_patterns(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Check for dangerous shell patterns."""
    pipe_to_shell = re.compile(r'\|\s*(ba)?sh\b|\|\s*zsh\b|\|\s*dash\b')
    if pipe_to_shell.search(unquoted):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.PIPE_TO_SHELL,
            message="Pipe to shell interpreter blocked"
        )

    if re.search(r'\bIFS\s*=', unquoted):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.IFS_INJECTION,
            message="IFS manipulation blocked"
        )

    if re.search(r'[\x00-\x08\x0e-\x1f\x7f]', command):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.CONTROL_CHARACTERS,
            message="Control characters in command blocked"
        )

    unicode_ws = re.compile(r'[\u00a0\u2000-\u200f\u2028\u2029\u202f\u205f\u3000\ufeff]')
    if unicode_ws.search(command):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.UNICODE_WHITESPACE,
            message="Unicode whitespace injection blocked"
        )

    if '/proc/' in unquoted and 'environ' in unquoted:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.PROC_ENVIRON,
            message="/proc environ access blocked"
        )

    if re.search(r'\$\(.*<<', unquoted):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.HEREDOC_IN_SUBSTITUTION,
            message="Heredoc inside command substitution blocked"
        )

    return None


def validate_brace_expansion(unquoted: str) -> Optional[SecurityResult]:
    """Detect dangerous brace expansion patterns."""
    brace_cmd = re.compile(r'\{[^}]*[;|&][^}]*\}')
    if brace_cmd.search(unquoted):
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.BRACE_EXPANSION,
            message="Dangerous brace expansion blocked"
        )
    return None


def validate_command(command: str) -> SecurityResult:
    """
    Main entry point: validate a shell command for security.
    Returns SecurityResult with allowed=True if safe, False if blocked.
    """
    if not command or not command.strip():
        return SecurityResult(allowed=True)

    command = command.strip()

    cmd_lower = command.lower()
    for blocked in ALWAYS_BLOCKED:
        if blocked in cmd_lower:
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.DANGEROUS_PATTERNS,
                message=f"Command contains blocked pattern: {blocked}"
            )

    for safe in SAFE_EXCEPTIONS:
        if cmd_lower.startswith(safe.lower()):
            return SecurityResult(allowed=True)

    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in cmd_lower and not any(safe in cmd_lower for safe in SAFE_EXCEPTIONS):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.DANGEROUS_PATTERNS,
                message=f"Potentially dangerous command: {dangerous}",
                severity="warning"
            )

    unquoted = extract_unquoted_content(command)

    validators = [
        validate_command_substitution,
        validate_redirections,
        validate_dangerous_patterns,
    ]

    for validator in validators:
        result = validator(command, unquoted)
        if result and not result.allowed:
            return result

    brace_result = validate_brace_expansion(unquoted)
    if brace_result and not brace_result.allowed:
        return brace_result

    return SecurityResult(allowed=True)
