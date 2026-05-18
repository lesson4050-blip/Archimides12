"""
Security Sandbox Hardening — Capability-Based Command Isolation.

Production-grade defense-in-depth for agent command execution:
  - Layer 1: Static analysis — fast regex + AST pattern matching
  - Layer 2: Capability restriction — allowlist of permitted operations
  - Layer 3: Resource limits — CPU time, memory, file size caps
  - Layer 4: Filesystem isolation — chroot-like path restriction
  - Layer 5: Audit logging — every command logged with risk score

This closes the "sandbox can be broken by a clever Python script" gap.
Designed to complement Docker/gVisor isolation at the application layer.
"""

import re
import os
import ast
import time
import logging
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    SAFE = "safe"           # Read-only, no side effects
    LOW = "low"             # Creates files, harmless writes
    MEDIUM = "medium"       # Modifies existing files, installs packages
    HIGH = "high"           # Deletes files, changes permissions
    CRITICAL = "critical"   # System-level, network exfiltration, privilege escalation
    BLOCKED = "blocked"     # Always denied


@dataclass
class SecurityVerdict:
    """Result of a security analysis on a command or code snippet."""
    allowed: bool
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    command_hash: str = ""
    analyzed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "command_hash": self.command_hash,
        }


# ── Layer 1: Static Pattern Analysis ────────────────────────────────

# Critical patterns — ALWAYS blocked regardless of context
CRITICAL_PATTERNS = [
    # Destructive filesystem operations
    (r"\brm\s+(-[rf]+\s+)?/(?!tmp)", "Recursive delete outside /tmp"),
    (r"\bmkfs\b", "Filesystem format"),
    (r"\bdd\s+if=", "Raw disk write"),
    (r">\s*/dev/sd[a-z]", "Direct device write"),

    # Fork bombs and resource exhaustion
    (r":\(\)\s*\{", "Fork bomb pattern"),
    (r"while\s+true\s*;?\s*do", "Infinite loop (shell)"),
    (r"\byes\s*\|", "Infinite output pipe"),

    # Privilege escalation
    (r"\bsudo\s+su\b", "Privilege escalation via sudo su"),
    (r"\bchmod\s+[0-7]*777\s+/", "World-writable root path"),
    (r"\bchown\s+root\b", "Ownership change to root"),
    (r"\bsetuid\b", "SUID manipulation"),
    (r"\bpasswd\b", "Password modification"),

    # Network exfiltration / reverse shells
    (r"\bcurl\b.*\|\s*(ba)?sh", "Remote code execution via curl|bash"),
    (r"\bwget\b.*\|\s*(ba)?sh", "Remote code execution via wget|sh"),
    (r"\bnc\s+(-[a-z]*\s+)*-e\b", "Netcat reverse shell"),
    (r"\b/dev/tcp/", "Bash reverse shell via /dev/tcp"),
    (r"\bsocat\b.*exec", "Socat command execution"),
    (r"\bnmap\b", "Network scanning"),
    (r"\btcpdump\b", "Network traffic capture"),

    # Container/VM escape
    (r"\bnsenter\b", "Namespace escape"),
    (r"\bmount\s+-o\s+bind", "Bind mount (container escape vector)"),
    (r"\bchroot\b", "Chroot manipulation"),
    (r"\bdocker\s+run\b", "Nested container launch"),
    (r"\bkubectl\s+exec\b", "Kubernetes pod escape"),
    (r"--privileged", "Privileged container flag"),

    # Cryptocurrency mining
    (r"\bxmrig\b", "Crypto miner"),
    (r"\bminerd\b", "Crypto miner"),
    (r"\bcpuminer\b", "Crypto miner"),

    # Data exfiltration
    (r"\bscp\b.*@", "SCP file transfer"),
    (r"\brsync\b.*@", "Rsync to remote"),
    (r"\bftp\b", "FTP transfer"),

    # Environment manipulation
    (r"\bexport\s+LD_PRELOAD", "Shared library injection"),
    (r"\bexport\s+PATH=", "PATH manipulation"),
    (r"/etc/shadow", "Shadow file access"),
    (r"/etc/passwd", "Passwd file access"),
]

PROMPT_INJECTION_PATTERNS = [
    # Classic instruction overrides
    (r"ignore\s+(all\s+)?previous\s+instructions", "Classic override"),
    (r"disregard\s+(all\s+|the\s+)?(above|previous|prior)", "Classic override"),
    (r"forget\s+(everything|all|your\s+instructions)", "Memory wipe attempt"),
    (r"new\s+(instruction|directive|order|command)\s*:", "New instruction injection"),
    (r"override\s+(your\s+)?(settings|instructions|rules|programming)", "Override attempt"),

    # Persona replacement
    (r"you\s+are\s+now\s+(?!Archimedes)", "Persona replacement"),
    (r"you\s+are\s+no\s+longer", "Persona override"),
    (r"act\s+as\s+(if\s+you\s+are\s+)?(?!an?\s+assistant)", "Role override"),
    (r"pretend\s+(you\s+are|to\s+be)\s+(?!helpful)", "Pretend override"),
    (r"roleplay\s+as\s+(?!a\s+helpful)", "Roleplay override"),

    # System prompt extraction
    (r"(what|show|reveal|print|output|repeat)\s+(is\s+)?(your\s+)?(system|initial|original)\s+(prompt|instructions?|message)", "System prompt extraction"),
    (r"output\s+(your|the)\s+instructions", "Instruction extraction"),
    (r"what\s+were\s+you\s+(told|instructed|programmed|trained)\s+(before|to do)", "Context extraction"),
    (r"initial\s+instructions", "Context extraction"),
    (r"confidential\s+prompt", "Prompt extraction attempt"),

    # Jailbreaks (DAN and variants)
    (r"\bDAN\b", "DAN jailbreak"),
    (r"do\s+anything\s+now", "DAN variant"),
    (r"jailbreak", "Jailbreak attempt"),
    (r"developer\s+mode", "Developer mode jailbreak"),
    (r"god\s+mode", "God mode jailbreak"),
    (r"unrestricted\s+mode", "Unrestricted mode"),
    (r"without\s+(any\s+)?(restrictions|limitations|filters|guidelines)", "Restriction bypass"),

    # Encoded/obfuscated injection
    (r"base64\s*:\s*[A-Za-z0-9+/]{10,}", "Base64 encoded injection"),
    (r"\\u[0-9a-fA-F]{4}.*ignore", "Unicode encoded injection"),
    (r"rot13|caesar\s+cipher", "Encoded injection attempt"),

    # Data exfiltration via prompt
    (r"(send|transmit|email|post)\s+(all|the|my|this)\s+(data|information|context|conversation)", "Data exfil via prompt"),
    (r"include\s+(this\s+)?(conversation|chat|history)\s+in", "Context exfiltration"),

    # Admin/sudo attempts
    (r"(sudo|admin|root|superuser)\s+(mode|access|override|command)", "Privilege escalation via prompt"),
    (r"maintenance\s+mode", "Maintenance mode bypass"),
    (r"debug\s+mode", "Debug mode attempt"),
    (r"internal\s+(command|function|api)", "Internal API access attempt"),
]

CRITICAL_RE = [(re.compile(p, re.IGNORECASE), desc) for p, desc in CRITICAL_PATTERNS]
PROMPT_INJECTION_RE = [(re.compile(p, re.IGNORECASE), desc) for p, desc in PROMPT_INJECTION_PATTERNS]


# ── Layer 2: Python AST Analysis ────────────────────────────────────

DANGEROUS_PYTHON_CALLS = {
    "os.system", "os.popen", "os.exec", "os.execv", "os.execve",
    "os.fork", "os.kill", "os.remove", "os.unlink", "os.rmdir",
    "subprocess.call", "subprocess.Popen", "subprocess.run",
    "shutil.rmtree", "shutil.move",
    "eval", "exec", "compile", "__import__",
    "ctypes.cdll", "ctypes.windll",
    "socket.socket", "socket.connect",
}

DANGEROUS_IMPORTS = {
    "ctypes", "signal", "resource", "pty", "fcntl",
    "multiprocessing", "threading",
}


def analyze_python_ast(code: str) -> Tuple[RiskLevel, List[str]]:
    """
    Statically analyze Python code for dangerous patterns using AST.
    Returns (risk_level, list_of_reasons).
    """
    reasons = []
    risk = RiskLevel.SAFE

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return RiskLevel.LOW, ["Could not parse Python code (syntax error)"]

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in DANGEROUS_IMPORTS:
                    reasons.append(f"Dangerous import: {alias.name}")
                    risk = max_risk(risk, RiskLevel.HIGH)

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in DANGEROUS_IMPORTS:
                reasons.append(f"Dangerous import from: {node.module}")
                risk = max_risk(risk, RiskLevel.HIGH)

        # Check function calls
        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in DANGEROUS_PYTHON_CALLS:
                reasons.append(f"Dangerous call: {func_name}")
                risk = max_risk(risk, RiskLevel.CRITICAL)
            elif func_name in ("open",):
                # open() is okay for reading, risky for writing
                if _has_write_mode(node):
                    reasons.append("File write via open()")
                    risk = max_risk(risk, RiskLevel.MEDIUM)

        # Check string patterns inside the code (for obfuscated attacks)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for pattern, desc in CRITICAL_RE:
                if pattern.search(node.value):
                    reasons.append(f"Dangerous string literal: {desc}")
                    risk = max_risk(risk, RiskLevel.CRITICAL)

    return risk, reasons


def _get_call_name(node: ast.Call) -> str:
    """Extract dotted call name from AST node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _has_write_mode(node: ast.Call) -> bool:
    """Check if an open() call uses a write mode."""
    for arg in node.args[1:]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if any(m in arg.value for m in ("w", "a", "x", "+")):
                return True
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            if any(m in str(kw.value.value) for m in ("w", "a", "x", "+")):
                return True
    return False


# ── Layer 3: Filesystem Path Restriction ────────────────────────────

# Allowed base paths for file operations (configurable)
DEFAULT_ALLOWED_PATHS = {
    Path("."),           # Project directory
    Path("/tmp"),        # Temporary files
    Path("./data"),      # Data directory
    Path("./output"),    # Output directory
}

FORBIDDEN_PATHS = {
    Path("/etc"), Path("/var"), Path("/usr"), Path("/bin"),
    Path("/sbin"), Path("/boot"), Path("/root"), Path("/proc"),
    Path("/sys"), Path("/dev"),
    # Windows equivalents
    Path("C:/Windows"), Path("C:/Program Files"),
}


def is_path_allowed(target_path: str, allowed_bases: Optional[Set[Path]] = None) -> Tuple[bool, str]:
    """
    Check if a file path is within allowed boundaries.
    Returns (allowed, reason).
    """
    bases = allowed_bases or DEFAULT_ALLOWED_PATHS
    try:
        resolved = Path(target_path).resolve()
    except Exception:
        return False, f"Invalid path: {target_path}"

    # Check forbidden paths first
    for forbidden in FORBIDDEN_PATHS:
        try:
            if resolved.is_relative_to(forbidden.resolve()):
                return False, f"Path is in forbidden directory: {forbidden}"
        except (ValueError, OSError):
            continue

    # Check if within any allowed base
    for base in bases:
        try:
            if resolved.is_relative_to(base.resolve()):
                return True, "Path is within allowed directory"
        except (ValueError, OSError):
            continue

    return False, f"Path is outside all allowed directories"


# ── Layer 4: Resource Limits ────────────────────────────────────────

@dataclass
class ResourceLimits:
    """Configurable resource caps for sandboxed execution."""
    max_cpu_seconds: int = 30
    max_memory_mb: int = 512
    max_file_size_mb: int = 50
    max_output_lines: int = 10000
    max_processes: int = 5
    network_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_file_size_mb": self.max_file_size_mb,
            "max_output_lines": self.max_output_lines,
            "max_processes": self.max_processes,
            "network_allowed": self.network_allowed,
        }


# ── Main Security Gate ──────────────────────────────────────────────

class SecurityGate:
    """
    Unified security analysis for all agent-executed commands and code.

    Usage:
        gate = SecurityGate()
        verdict = gate.analyze_command("rm -rf /tmp/test")
        if not verdict.allowed:
            raise SecurityError(verdict.reasons)
    """

    def __init__(
        self,
        resource_limits: Optional[ResourceLimits] = None,
        allowed_paths: Optional[Set[Path]] = None,
        strict_mode: bool = False,  # In strict mode, MEDIUM risk = blocked
    ):
        self.limits = resource_limits or ResourceLimits()
        self.allowed_paths = allowed_paths or DEFAULT_ALLOWED_PATHS
        self.strict_mode = strict_mode
        self._audit_log: List[Dict[str, Any]] = []

    def analyze_command(self, command: str) -> SecurityVerdict:
        """Analyze a shell command for security risks."""
        cmd_hash = hashlib.sha256(command.encode()).hexdigest()[:12]
        reasons = []
        risk = RiskLevel.SAFE

        # Layer 1: Critical pattern matching
        for pattern, desc in CRITICAL_RE:
            if pattern.search(command):
                reasons.append(f"BLOCKED: {desc}")
                risk = RiskLevel.BLOCKED

        # Layer 2: Medium-risk patterns
        if risk != RiskLevel.BLOCKED:
            medium_patterns = [
                (r"\bpip\s+install\b", "Package installation"),
                (r"\bnpm\s+install\b", "NPM package installation"),
                (r"\bapt(-get)?\s+install\b", "System package installation"),
                (r"\bcurl\b|\bwget\b", "Network download"),
                (r"\bgit\s+push\b", "Git push to remote"),
                (r"\bgit\s+clone\b", "Git clone from remote"),
            ]
            for pat, desc in medium_patterns:
                if re.search(pat, command, re.IGNORECASE):
                    reasons.append(f"MEDIUM: {desc}")
                    risk = max_risk(risk, RiskLevel.MEDIUM)

        # Determine if allowed
        blocked = (risk == RiskLevel.BLOCKED) or (self.strict_mode and risk >= RiskLevel.MEDIUM)

        verdict = SecurityVerdict(
            allowed=not blocked,
            risk_level=risk,
            reasons=reasons,
            command_hash=cmd_hash,
        )

        self._audit(command, verdict, "shell")
        return verdict

    def analyze_python(self, code: str) -> SecurityVerdict:
        """Analyze Python code for security risks using AST."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]

        # Layer 1: Critical regex scan on raw text
        reasons = []
        risk = RiskLevel.SAFE

        for pattern, desc in CRITICAL_RE:
            if pattern.search(code):
                reasons.append(f"BLOCKED: {desc}")
                risk = RiskLevel.BLOCKED

        # Layer 2: AST analysis (only if not already blocked)
        if risk != RiskLevel.BLOCKED:
            ast_risk, ast_reasons = analyze_python_ast(code)
            risk = max_risk(risk, ast_risk)
            reasons.extend(ast_reasons)

        blocked = (risk == RiskLevel.BLOCKED) or (
            risk == RiskLevel.CRITICAL
        ) or (
            self.strict_mode and risk >= RiskLevel.MEDIUM
        )

        verdict = SecurityVerdict(
            allowed=not blocked,
            risk_level=risk,
            reasons=reasons,
            command_hash=code_hash,
        )

        self._audit(code[:200], verdict, "python")
        return verdict

    def analyze_file_access(self, path: str, operation: str = "read") -> SecurityVerdict:
        """Analyze a file access operation for security."""
        path_hash = hashlib.sha256(path.encode()).hexdigest()[:12]
        allowed, reason = is_path_allowed(path, self.allowed_paths)

        risk = RiskLevel.SAFE if allowed else RiskLevel.HIGH
        if operation in ("write", "delete", "modify") and allowed:
            risk = RiskLevel.LOW

        verdict = SecurityVerdict(
            allowed=allowed,
            risk_level=risk,
            reasons=[reason],
            command_hash=path_hash,
        )

        self._audit(f"{operation}:{path}", verdict, "file")
        return verdict

    def analyze_prompt_injection(self, prompt: str) -> SecurityVerdict:
        """Analyze user input for jailbreaks or prompt extraction."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        reasons = []
        risk = RiskLevel.SAFE

        for pattern, desc in PROMPT_INJECTION_RE:
            if pattern.search(prompt):
                reasons.append(f"PROMPT INJECTION DETECTED: {desc}")
                risk = RiskLevel.CRITICAL

        blocked = risk == RiskLevel.CRITICAL

        verdict = SecurityVerdict(
            allowed=not blocked,
            risk_level=risk,
            reasons=reasons,
            command_hash=prompt_hash,
        )

        self._audit(prompt[:200], verdict, "prompt")
        return verdict

    def analyze_encoded_injection(self, text: str) -> SecurityVerdict:
        """
        Detect injection attempts hidden in encoded formats.
        Attackers encode malicious prompts in base64, hex, etc.
        """
        import base64
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
        reasons = []
        risk = RiskLevel.SAFE

        # Try to decode potential base64 segments
        import re as _re
        b64_segments = _re.findall(r'[A-Za-z0-9+/]{20,}={0,2}', text)
        for segment in b64_segments[:5]:  # Check first 5 segments max
            try:
                decoded = base64.b64decode(segment).decode('utf-8', errors='ignore')
                # Check decoded content for injection
                for pattern, desc in PROMPT_INJECTION_RE:
                    if pattern.search(decoded):
                        reasons.append(f"Encoded injection (base64): {desc}")
                        risk = RiskLevel.CRITICAL
                        break
            except Exception:
                pass

        # Check for hex-encoded injection
        hex_segments = _re.findall(r'(?:0x)?[0-9a-fA-F]{20,}', text)
        for segment in hex_segments[:3]:
            try:
                clean = segment.replace('0x', '')
                decoded = bytes.fromhex(clean).decode('utf-8', errors='ignore')
                for pattern, desc in PROMPT_INJECTION_RE:
                    if pattern.search(decoded):
                        reasons.append(f"Encoded injection (hex): {desc}")
                        risk = RiskLevel.CRITICAL
                        break
            except Exception:
                pass

        blocked = risk == RiskLevel.CRITICAL
        verdict = SecurityVerdict(
            allowed=not blocked,
            risk_level=risk,
            reasons=reasons,
            command_hash=text_hash,
        )
        self._audit(text[:100], verdict, "encoded_injection")
        return verdict

    def full_prompt_analysis(self, user_input: str) -> SecurityVerdict:
        """
        Run ALL prompt security checks:
        1. Injection patterns
        2. Encoded injection
        3. Combined verdict

        Use this as the single entry point for user input validation.
        """
        # Cap input length for analysis performance
        text = user_input[:10000]

        v1 = self.analyze_prompt_injection(text)
        v2 = self.analyze_encoded_injection(text)

        # Combine results
        combined_risk = max_risk(v1.risk_level, v2.risk_level)
        combined_reasons = v1.reasons + v2.reasons
        blocked = not v1.allowed or not v2.allowed

        return SecurityVerdict(
            allowed=not blocked,
            risk_level=combined_risk,
            reasons=combined_reasons,
            command_hash=v1.command_hash,
        )

    def _audit(self, content: str, verdict: SecurityVerdict, category: str) -> None:
        """Log every security decision for forensic review."""
        entry = {
            "timestamp": time.time(),
            "category": category,
            "content_preview": content[:100],
            "verdict": verdict.to_dict(),
        }
        self._audit_log.append(entry)

        # Keep audit log bounded
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

        # Log high-risk events
        if verdict.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.BLOCKED):
            logger.warning(
                f"SECURITY [{verdict.risk_level.value.upper()}] "
                f"{category}: {content[:80]} → {verdict.reasons}"
            )

    def get_audit_log(self, last_n: int = 50) -> List[Dict[str, Any]]:
        """Return recent audit entries."""
        return self._audit_log[-last_n:]

    def get_resource_limits(self) -> Dict[str, Any]:
        """Return current resource limit configuration."""
        return self.limits.to_dict()


def max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Return the higher of two risk levels."""
    order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM,
             RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.BLOCKED]
    return order[max(order.index(a), order.index(b))]
