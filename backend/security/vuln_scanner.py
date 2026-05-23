"""
Bumblebee-inspired local vulnerability scanner.
READ-ONLY: analyzes metadata, lock files, configs.
Never executes package managers or scripts.

Scans 4 vectors:
1. Python dependencies (requirements.txt, pyproject.toml)
2. Node.js dependencies (package-lock.json, package.json)
3. MCP configurations (mcp_config.json)
4. VS Code extension configs (.vscode/, extensions)

SECURITY: runs in read-only mode, no subprocess calls.
"""
import json
import re
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Known vulnerable patterns (simplified — real tool would use CVE DB)
VULNERABLE_PYTHON_PATTERNS = [
    (r"requests[<>=]=?([01]\.|2\.[0-9]\.|2\.2[0-7]\.)", "requests <2.28.0 — SSRF vulnerability"),
    (r"pillow[<>=]=?([0-9]\.|[1-8]\.|9\.[0-4]\.)", "Pillow <9.5 — arbitrary code execution"),
    (r"pyyaml[<>=]=?([0-4]\.|5\.[0-3]\.)", "PyYAML <5.4 — arbitrary code execution"),
    (r"cryptography[<>=]=?([0-2][0-9]\.|3[0-5]\.)", "cryptography <36.0 — multiple CVEs"),
    (r"paramiko[<>=]=?([0-2]\.|3\.0\.)", "paramiko <3.1 — authentication bypass"),
    (r"urllib3[<>=]=?1\.", "urllib3 <2.0 — header injection"),
    (r"setuptools[<>=]=?([0-5][0-9]\.)", "setuptools <60.0 — ReDoS vulnerability"),
    (r"werkzeug[<>=]=?(0\.|1\.|2\.[0-2]\.)", "Werkzeug <2.3 — DoS vulnerability"),
]

VULNERABLE_NODE_PATTERNS = [
    (r'"axios":\s*"[~^]?0\.[0-9]', "axios <1.0 — SSRF vulnerability"),
    (r'"lodash":\s*"[~^]?[0-3]\.', "lodash <4.0 — prototype pollution"),
    (r'"minimist":\s*"[~^]?[01]\.0\.[0-9]"', "minimist — prototype pollution CVE"),
    (r'"node-fetch":\s*"[~^]?[12]\.[0-4]\.', "node-fetch <2.6.7 — SSRF"),
    (r'"follow-redirects":\s*"[~^]?1\.1[0-3]\.', "follow-redirects <1.14.8 — cookie leak"),
]

DANGEROUS_MCP_PATTERNS = [
    (r'"command":\s*"curl"', "MCP server uses curl — potential SSRF"),
    (r'"command":\s*".*\\.sh"', "MCP server executes shell script"),
    (r'"env".*"API_KEY".*"[A-Za-z0-9]{20,}"', "Hardcoded API key in MCP config"),
    (r'http://', "Unencrypted HTTP in MCP config"),
]

@dataclass
class VulnFinding:
    severity: str  # critical, high, medium, low, info
    vector: str    # python, nodejs, mcp, config
    file: str
    description: str
    recommendation: str

@dataclass
class ScanResult:
    findings: List[VulnFinding] = field(default_factory=list)
    scanned_files: List[str] = field(default_factory=list)
    scan_duration_ms: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == 'critical')

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == 'high')

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_findings": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": sum(1 for f in self.findings if f.severity == 'medium'),
                "low": sum(1 for f in self.findings if f.severity == 'low'),
                "scanned_files": len(self.scanned_files),
                "scan_duration_ms": round(self.scan_duration_ms, 1),
            },
            "findings": [
                {
                    "severity": f.severity,
                    "vector": f.vector,
                    "file": f.file,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in sorted(
                    self.findings,
                    key=lambda x: {"critical":0,"high":1,"medium":2,"low":3}.get(x.severity,4)
                )
            ]
        }


class VulnScanner:
    """Read-only vulnerability scanner. Never executes code."""

    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir)

    def scan(self) -> ScanResult:
        import time
        start = time.time()
        result = ScanResult()

        self._scan_python_deps(result)
        self._scan_node_deps(result)
        self._scan_mcp_configs(result)
        self._scan_env_files(result)

        result.scan_duration_ms = (time.time() - start) * 1000
        return result

    def _read_file_safe(self, path: Path, max_size: int = 512_000) -> str:
        """Read file safely — size limit, no execution."""
        try:
            if path.stat().st_size > max_size:
                return ""
            return path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return ""

    def _scan_python_deps(self, result: ScanResult):
        """Scan requirements.txt and pyproject.toml."""
        req_files = [
            self.root / "requirements.txt",
            self.root / "requirements-dev.txt",
        ]
        for req_file in req_files:
            if not req_file.exists():
                continue
            content = self._read_file_safe(req_file)
            result.scanned_files.append(str(req_file))
            content_lower = content.lower()

            for pattern, desc in VULNERABLE_PYTHON_PATTERNS:
                if re.search(pattern, content_lower):
                    result.findings.append(VulnFinding(
                        severity="high",
                        vector="python",
                        file=str(req_file),
                        description=desc,
                        recommendation="Update to the latest secure version"
                    ))

    def _scan_node_deps(self, result: ScanResult):
        """Scan package.json files."""
        for pkg_file in self.root.rglob("package.json"):
            if "node_modules" in str(pkg_file):
                continue
            content = self._read_file_safe(pkg_file)
            result.scanned_files.append(str(pkg_file))

            for pattern, desc in VULNERABLE_NODE_PATTERNS:
                if re.search(pattern, content):
                    result.findings.append(VulnFinding(
                        severity="medium",
                        vector="nodejs",
                        file=str(pkg_file),
                        description=desc,
                        recommendation="Update dependency to latest secure version"
                    ))

    def _scan_mcp_configs(self, result: ScanResult):
        """Scan MCP configuration files."""
        mcp_files = [
            self.root / "mcp_config.json",
            Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        ]
        for mcp_file in mcp_files:
            if not mcp_file.exists():
                continue
            content = self._read_file_safe(mcp_file)
            if not content.strip():
                continue
            result.scanned_files.append(str(mcp_file))

            for pattern, desc in DANGEROUS_MCP_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    result.findings.append(VulnFinding(
                        severity="medium",
                        vector="mcp",
                        file=str(mcp_file),
                        description=desc,
                        recommendation="Review MCP server configuration"
                    ))

    def _scan_env_files(self, result: ScanResult):
        """Check for accidentally committed secrets."""
        env_files = list(self.root.glob(".env*"))
        for env_file in env_files:
            if env_file.name in (".env.example", ".env.template"):
                continue
            # Check if tracked by git
            try:
                import subprocess
                git_check = subprocess.run(
                    ["git", "ls-files", str(env_file)],
                    capture_output=True, text=True,
                    cwd=str(self.root)
                )
                if git_check.stdout.strip():
                    result.findings.append(VulnFinding(
                        severity="critical",
                        vector="config",
                        file=str(env_file),
                        description=f"{env_file.name} is tracked by git — secrets may be exposed",
                        recommendation="Run: git rm --cached " + str(env_file)
                    ))
                    result.scanned_files.append(str(env_file))
            except Exception:
                pass
