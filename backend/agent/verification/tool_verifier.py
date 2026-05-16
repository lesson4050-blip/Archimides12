"""
ToolVerifier — lightweight per-tool-call verification.
Runs AFTER every tool execution, BEFORE the result is returned to the LLM.
Does NOT call LLM — pure deterministic checks only.
Fast: <5ms per check.
"""
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ToolVerifyStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class ToolVerifyResult:
    status: ToolVerifyStatus
    tool_name: str
    issues: list
    auto_retry: bool = False
    corrected_output: Optional[str] = None

class ToolVerifier:
    """
    Deterministic rule-based verification for each tool call result.
    No LLM calls — instant, cheap, always runs.
    """

    # Tools that MUST return success=True to be valid
    MUST_SUCCEED = {"search", "shell", "file", "web_read"}
    
    # Patterns that indicate a tool produced garbage output
    GARBAGE_PATTERNS = [
        r"<function=\w+>",           # Groq hallucination format
        r"<\w+>\{",                   # XML tool call leak
        r"undefined",                 # JS undefined in output
        r"NoneType.*has no attribute", # Python error in output
        r"Traceback \(most recent",   # Raw Python exception
    ]
    
    # Shell commands that are dangerous and should never have run
    DANGEROUS_SHELL_PATTERNS = [
        r"rm\s+-rf\s+/",
        r"dd\s+if=/dev/zero",
        r"mkfs\.",
        r":\(\)\s*\{.*\}",  # Fork bomb
    ]

    def verify(
        self, 
        tool_name: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        context: Optional[str] = None
    ) -> ToolVerifyResult:
        """
        Verify a single tool call result.
        Returns ToolVerifyResult with status and any issues found.
        """
        issues = []
        
        # 1. Check if tool claims success
        if tool_name in self.MUST_SUCCEED:
            if not result.get("success", True):
                error = result.get("error", "unknown error")
                issues.append(f"Tool failed: {error}")
        
        # 2. Check for garbage output patterns
        output = str(result.get("output", ""))
        for pattern in self.GARBAGE_PATTERNS:
            if re.search(pattern, output):
                issues.append(f"Garbage pattern detected: {pattern}")
        
        # 3. Search tool: verify it actually returned results
        if tool_name == "search":
            if not output or len(output) < 20:
                issues.append("Search returned empty or too-short results")
        
        # 4. Shell tool: verify no dangerous commands ran
        if tool_name == "shell":
            command = str(params.get("command", "") or params.get("action", ""))
            for pattern in self.DANGEROUS_SHELL_PATTERNS:
                if re.search(pattern, command):
                    issues.append(f"DANGEROUS command detected: {command[:100]}")
            
            # Check if shell returned an actual error
            output_lower = output.lower()
            if any(err in output_lower for err in ["command not found", "permission denied", "no such file"]):
                issues.append(f"Shell error in output: {output[:100]}")
        
        # 5. File tool: verify file operations succeeded
        if tool_name == "file":
            action = str(params.get("action", ""))
            if action in ("write", "edit") and not result.get("success"):
                issues.append(f"File {action} operation failed")
        
        # 6. Code output: basic syntax check for Python
        if tool_name in ("shell", "code_editor") and "def " in output:
            try:
                import ast
                # Extract code blocks
                code_blocks = re.findall(r"```python\n(.*?)\n```", output, re.DOTALL)
                for block in code_blocks:
                    ast.parse(block)
            except SyntaxError as e:
                issues.append(f"Python syntax error in output: {e}")
        
        # Determine status
        if not issues:
            return ToolVerifyResult(
                status=ToolVerifyStatus.PASS,
                tool_name=tool_name,
                issues=[]
            )
        
        # Dangerous issues = FAIL, others = WARN
        is_critical = any(
            "DANGEROUS" in i or "failed" in i.lower() or "Traceback" in i
            for i in issues
        )
        
        return ToolVerifyResult(
            status=ToolVerifyStatus.FAIL if is_critical else ToolVerifyStatus.WARN,
            tool_name=tool_name,
            issues=issues,
            auto_retry=is_critical
        )

# Global singleton
tool_verifier = ToolVerifier()
