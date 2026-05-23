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
    ZSH_SPECIFIC = 15
    HEREDOC_INJECTION = 16
    INVISIBLE_CHARACTERS = 17
    NESTED_SUBSTITUTION = 18
    PERMISSION_REQUIRED = 19


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


# ── Zsh-specific attack patterns ──

ZSH_DANGEROUS_BUILTINS = {
    "zmodload", "emulate", "ztcp", "zsocket",
    "zcompile", "autoload", "zle", "bindkey",
    "sched", "zpty", "zformat", "zstyle",
}

ZSH_ATTACK_PATTERNS = [
    (re.compile(r'emulate\s+-[LR]?\s*(?:sh|ksh|csh)'), "Zsh emulation mode switch"),
    (re.compile(r'zmodload\s+zsh/'), "Zsh module loading"),
    (re.compile(r'ztcp\s'), "Zsh TCP socket access"),
    (re.compile(r'zsocket\s'), "Zsh socket access"),
    (re.compile(r'zcompile\s'), "Zsh bytecode compilation"),
    (re.compile(r'autoload\s+-U?z?\s'), "Zsh function autoloading"),
]

# ── Heredoc patterns ──

HEREDOC_PATTERNS = [
    (re.compile(r'<<\s*(\w+).*<<\s*\1', re.DOTALL), "Nested heredoc with same delimiter"),
    (re.compile(r'<<\s*["\']?EOF["\']?\s*.*\$\(', re.DOTALL), "Command substitution inside heredoc"),
    (re.compile(r'<<\s*\\'), "Escaped heredoc delimiter"),
]

# ── Invisible character patterns ──

INVISIBLE_CHARS = [
    ('\u200b', 'zero-width space'),
    ('\u200c', 'zero-width non-joiner'),
    ('\u200d', 'zero-width joiner'),
    ('\u2060', 'word joiner'),
    ('\ufeff', 'BOM'),
    ('\u00ad', 'soft hyphen'),
    ('\u200e', 'left-to-right mark'),
    ('\u200f', 'right-to-left mark'),
    ('\u202a', 'left-to-right embedding'),
    ('\u202b', 'right-to-left embedding'),
    ('\u202c', 'pop directional formatting'),
    ('\u2066', 'left-to-right isolate'),
    ('\u2067', 'right-to-left isolate'),
    ('\u2068', 'first strong isolate'),
    ('\u2069', 'pop directional isolate'),
    ('\u061c', 'Arabic letter mark'),
]

# ── Commands requiring explicit user approval ──

PERMISSION_REQUIRED_COMMANDS = {
    "rm -rf", "rm -r", "rmdir",
    "chmod", "chown", "chgrp",
    "kill", "killall", "pkill",
    "systemctl", "service",
    "mount", "umount",
    "iptables", "ufw",
    "crontab",
    "useradd", "userdel", "usermod",
    "passwd",
    "docker rm", "docker rmi", "docker system prune",
}


def extract_unquoted_content(command: str) -> str:
    """
    Strip quoted content from command, preserving only unquoted parts.
    This prevents false positives from patterns inside string literals.
    """
    # Strip null bytes before processing — prevents parser desync
    command = command.replace('\x00', '')
    
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


# ── Sensitive file read patterns (FIX-6) ──

SENSITIVE_READ_PATTERNS = [
    (re.compile(r'\b(cat|less|more|head|tail|tac|nl|strings)\s+/etc/(passwd|shadow|sudoers|gshadow|master\.passwd)'),
     "Reading sensitive system credential file"),
    (re.compile(r'\b(cat|less|more|head|tail)\s+.*\.(pem|key|p12|pfx|jks|keystore)'),
     "Reading private key or certificate file"),
    (re.compile(r'\b(cat|less|more|head|tail)\s+.*/(\.env|\.aws/credentials|\.ssh/id_)'),
     "Reading secrets/credentials file"),
]


def validate_sensitive_reads(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Detect commands that read sensitive system or credential files."""
    for pattern, desc in SENSITIVE_READ_PATTERNS:
        if pattern.search(unquoted):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.DANGEROUS_PATTERNS,
                message=f"Blocked: {desc}"
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


def validate_zsh_attacks(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Detect Zsh-specific attack vectors."""
    cmd_lower = unquoted.lower()
    for builtin in ZSH_DANGEROUS_BUILTINS:
        if builtin in cmd_lower:
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.ZSH_SPECIFIC,
                message=f"Zsh dangerous builtin blocked: {builtin}"
            )
    for pattern, desc in ZSH_ATTACK_PATTERNS:
        if pattern.search(unquoted):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.ZSH_SPECIFIC,
                message=f"Zsh attack blocked: {desc}"
            )
    return None


def validate_heredoc(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Detect heredoc injection attempts."""
    for pattern, desc in HEREDOC_PATTERNS:
        if pattern.search(command):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.HEREDOC_INJECTION,
                message=f"Heredoc injection blocked: {desc}"
            )
    heredoc_count = len(re.findall(r'<<[-~]?\s*["\']?\w+["\']?', command))
    if heredoc_count > 2:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.HEREDOC_INJECTION,
            message=f"Excessive heredocs ({heredoc_count}) — possible injection"
        )
    return None


def validate_invisible_chars(command: str) -> Optional[SecurityResult]:
    """Detect invisible/Unicode control characters that obfuscate commands."""
    for char, name in INVISIBLE_CHARS:
        if char in command:
            hex_repr = f"U+{ord(char):04X}"
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.INVISIBLE_CHARACTERS,
                message=f"Invisible character: {name} ({hex_repr})"
            )
    for i, char in enumerate(command):
        if ord(char) < 32 and char not in ('\n', '\r', '\t'):
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.INVISIBLE_CHARACTERS,
                message=f"Control character U+{ord(char):04X} at position {i}"
            )
    return None


def validate_nested_substitution(command: str, unquoted: str) -> Optional[SecurityResult]:
    """Detect deeply nested command substitutions."""
    depth = 0
    max_depth = 0
    for i, char in enumerate(unquoted):
        if i > 0 and unquoted[i-1:i+1] == '$(':
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ')' and depth > 0:
            depth -= 1
    if max_depth > 2:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.NESTED_SUBSTITUTION,
            message=f"Deeply nested command substitution (depth={max_depth})"
        )
    return None


def check_permission_required(command: str) -> Optional[SecurityResult]:
    """Check if command requires explicit user approval (HITL)."""
    cmd_lower = command.strip().lower()
    for perm_cmd in PERMISSION_REQUIRED_COMMANDS:
        if cmd_lower.startswith(perm_cmd) or f" {perm_cmd}" in cmd_lower:
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.PERMISSION_REQUIRED,
                message=f"Command requires user approval: {perm_cmd}",
                severity="permission_required"
            )
    return None


def validate_command(command: str) -> SecurityResult:
    """
    Main entry point — validate a shell command through all security layers.

    Layer order: invisible chars → always blocked → safe exceptions →
    zsh → heredoc → nested substitution → command substitution →
    redirections → dangerous patterns → brace expansion → permission check.
    """
    if not command or not command.strip():
        return SecurityResult(allowed=True, message="Empty command")

    # ═══ LAYER -1: NULL BYTE CHECK (CVE-class vulnerability) ═══
    # Must run before any parsing — null bytes corrupt quote tracking
    if '\x00' in command:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.INVISIBLE_CHARACTERS,
            message="Null byte injection attempt blocked (\\x00)"
        )

    # Also check for null bytes in various encodings
    if '%00' in command or '\\0' in command or '\\x00' in command:
        return SecurityResult(
            allowed=False,
            check_id=SecurityCheckID.INVISIBLE_CHARACTERS,
            message="Encoded null byte injection blocked"
        )

    # Layer 0: Invisible characters (check RAW command, before any parsing)
    result = validate_invisible_chars(command)
    if result:
        return result

    cmd_lower = command.strip().lower()
    for blocked in ALWAYS_BLOCKED:
        if blocked in cmd_lower:
            # Check if this is a permission-required command that was upgraded to ALWAYS_BLOCKED
            is_perm = any(perm in blocked for perm in PERMISSION_REQUIRED_COMMANDS)
            return SecurityResult(
                allowed=False,
                check_id=SecurityCheckID.DANGEROUS_PATTERNS,
                message=f"Always-blocked command: {blocked}",
                severity="permission_required" if is_perm else "blocked"
            )

    for safe in SAFE_EXCEPTIONS:
        if cmd_lower.startswith(safe):
            return SecurityResult(allowed=True, message="Safe exception matched")

    unquoted = extract_unquoted_content(command)

    # Layer 1: Zsh-specific attacks
    result = validate_zsh_attacks(command, unquoted)
    if result:
        return result

    # Layer 2: Heredoc injection
    result = validate_heredoc(command, unquoted)
    if result:
        return result

    # Layer 3: Nested command substitution
    result = validate_nested_substitution(command, unquoted)
    if result:
        return result

    # Layer 4: Command substitution
    result = validate_command_substitution(command, unquoted)
    if result:
        return result

    # Layer 5: Redirections
    result = validate_redirections(command, unquoted)
    if result:
        return result

    # Layer 6: Dangerous patterns
    result = validate_dangerous_patterns(command, unquoted)
    if result:
        return result

    # Layer 6.5: Sensitive file reads (FIX-6)
    result = validate_sensitive_reads(command, unquoted)
    if result:
        return result

    # Layer 7: Brace expansion
    result = validate_brace_expansion(unquoted)
    if result:
        return result

    # Layer 8: Permission check (HITL)
    result = check_permission_required(command)
    if result:
        return result

    return SecurityResult(allowed=True, message="All security checks passed")
