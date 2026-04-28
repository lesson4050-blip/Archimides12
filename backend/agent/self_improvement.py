"""
Archimedes Self-Improvement Engine.

Every time a tool call fails and is subsequently recovered, the system
stores the (error → fix) pattern. On subsequent encounters with similar
errors, the engine proactively suggests known fixes.

Features:
- Pattern normalization (strips volatile data: line numbers, paths, timestamps)
- Confidence scoring (tracks how many times each fix worked)
- Decay: patterns that haven't helped recently get lower priority
- Thread-safe: uses connection-per-call pattern for SQLite
"""
import aiosqlite
import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get(
    "SELF_IMPROVE_DB",
    os.path.join("data", "self_improvement.db")
)


async def _init_db():
    """Create a new connection with proper schema initialization."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        
        # Table 1: Raw Error Tracking
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                tool_name TEXT,
                raw_error TEXT,
                normalized_pattern TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Table 2: Confirmed Fixes (replaces 'lessons')
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS successful_fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_pattern TEXT NOT NULL,
                fix_pattern TEXT NOT NULL,
                tool_name TEXT DEFAULT '',
                success_count INTEGER DEFAULT 1,
                fail_count INTEGER DEFAULT 0,
                last_used TEXT DEFAULT (datetime('now')),
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Table 3: Complex Workflow Skills
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_intent TEXT NOT NULL,
                skill_payload TEXT NOT NULL,
                success_rate REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fixes_pattern
            ON successful_fixes(error_pattern)
        """)
        await conn.commit()


def _normalize_error(error: str) -> str:
    """
    Normalize an error string into a stable pattern.
    Strips line numbers, file paths, timestamps, and memory addresses.
    """
    pattern = error[:300]
    # 1. Replace UUIDs FIRST (before numbers are replaced)
    pattern = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        'UUID', pattern
    )
    # 2. Replace hex addresses
    pattern = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', pattern)
    # 3. Replace file paths (Unix and Windows)
    pattern = re.sub(r'[A-Za-z]:\\[^\s]+', 'PATH', pattern)
    pattern = re.sub(r'/[^\s]+', '/PATH', pattern)
    # 4. Replace numbers LAST
    pattern = re.sub(r'\b\d+\b', 'N', pattern)
    # 5. Normalize whitespace
    pattern = re.sub(r'\s+', ' ', pattern).strip()
    return pattern


async def log_error(error: str, tool_name: str, session_id: str = ""):
    """Log a raw error for analytics and future autonomous processing."""
    if not error: return
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            await conn.execute(
                "INSERT INTO error_logs (session_id, tool_name, raw_error, normalized_pattern) "
                "VALUES (?, ?, ?, ?)",
                (session_id, tool_name, error, _normalize_error(error))
            )
            await conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log error: {e}")

async def learn_from_error(
    error: str, fix: str, tool_name: str = "", success: bool = True
):
    """
    Store or update a fix pattern when agent recovers from an error.
    
    Args:
        error: The original error message
        fix: The fix that was applied
        tool_name: Which tool produced the error
        success: Whether the fix actually worked
    """
    if not error or not fix:
        return

    try:
        pattern = _normalize_error(error)
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT id, success_count, fail_count FROM successful_fixes "
                "WHERE error_pattern = ? AND tool_name = ?",
                (pattern, tool_name)
            )
            existing = await cursor.fetchone()

            if existing:
                if success:
                    await conn.execute(
                        "UPDATE successful_fixes SET success_count = success_count + 1, "
                        "last_used = datetime('now'), fix_pattern = ? "
                        "WHERE id = ?",
                        (fix[:500], existing[0])
                    )
                else:
                    await conn.execute(
                        "UPDATE successful_fixes SET fail_count = fail_count + 1 "
                        "WHERE id = ?",
                        (existing[0],)
                    )
            else:
                await conn.execute(
                    "INSERT INTO successful_fixes "
                    "(error_pattern, fix_pattern, tool_name) VALUES (?,?,?)",
                    (pattern, fix[:500], tool_name)
                )

            await conn.commit()
    except Exception as e:
        logger.warning(f"Self-improvement learn failed: {e}")


async def get_fix_hint(error: str, tool_name: str = "") -> Optional[str]:
    """
    Retrieve a previously learned fix for a similar error.
    
    Returns the most successful fix pattern, weighted by
    (success_count - fail_count) to avoid suggesting fixes that
    stopped working.
    """
    if not error:
        return None

    try:
        pattern = _normalize_error(error)
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            # Query with confidence scoring
            if tool_name:
                cursor = await conn.execute(
                    "SELECT fix_pattern FROM successful_fixes "
                    "WHERE error_pattern = ? AND tool_name = ? "
                    "AND (success_count - fail_count) > 0 "
                    "ORDER BY (success_count - fail_count) DESC LIMIT 1",
                    (pattern, tool_name)
                )
            else:
                cursor = await conn.execute(
                    "SELECT fix_pattern FROM successful_fixes "
                    "WHERE error_pattern = ? "
                    "AND (success_count - fail_count) > 0 "
                    "ORDER BY (success_count - fail_count) DESC LIMIT 1",
                    (pattern,)
                )
            row = await cursor.fetchone()

        return row[0] if row else None
    except Exception:
        return None


async def get_all_lessons(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve all learned lessons, sorted by effectiveness."""
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT error_pattern, fix_pattern, tool_name, "
                "success_count, fail_count, last_used "
                "FROM successful_fixes "
                "ORDER BY (success_count - fail_count) DESC "
                "LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()

        return [
            {
                "error_pattern": r[0],
                "fix_pattern": r[1],
                "tool_name": r[2],
                "success_count": r[3],
                "fail_count": r[4],
                "last_used": r[5],
                "confidence": r[3] / max(r[3] + r[4], 1),
            }
            for r in rows
        ]
    except Exception:
        return []


async def get_context_prompt(error: str, tool_name: str = "") -> str:
    """
    Generate a context string for the LLM that includes known fixes.
    Designed to be injected into executor prompts when errors occur.
    """
    hint = await get_fix_hint(error, tool_name)
    if hint:
        return (
            f"\n[SELF-IMPROVEMENT HINT] A similar error was seen before. "
            f"Previously successful fix: {hint}\n"
        )
    return ""


async def check_tool_safety(tool_name: str, params: dict) -> Tuple[bool, str]:
    """
    Pre-flight safety check for tool execution.
    Analyzes parameters and checks against historical failure loops.
    
    Returns:
        (is_safe, warning_message)
    """
    if tool_name == "shell":
        cmd = params.get("command", "").lower()
        # Destructive filesystem operations
        if "rm -rf /" in cmd or "del /s /q c:\\" in cmd:
            return False, "Dangerous system-level deletion command detected"
        # Fork bombs and resource exhaustion
        if ":(){ :|:& };:" in cmd or "while true" in cmd:
            return False, "Fork bomb or infinite loop detected"
        # Credential exposure
        if any(kw in cmd for kw in ["cat /etc/shadow", "cat /etc/passwd", "mimikatz"]):
            return False, "Credential exposure attempt detected"
        # Recursive deletions without safeguard
        if ("rm -rf" in cmd or "rmdir /s" in cmd) and (
            cmd.count("/") < 3 and "workspace" not in cmd
        ):
            return False, "Recursive deletion outside workspace scope"
        # Network exfiltration patterns
        if any(kw in cmd for kw in ["curl -d", "wget --post", "nc -e"]):
            return False, "Potential data exfiltration command blocked"
    
    if tool_name == "file":
        action = params.get("action", "")
        path = params.get("path", "").lower()
        # Block writes to system paths
        if action == "write" and any(
            path.startswith(p) for p in ["/etc/", "/usr/", "c:\\windows", "/system"]
        ):
            return False, "Writing to system-protected path blocked"

    # Check if this exact tool/params has failed consecutively
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM error_logs "
                "WHERE tool_name = ? AND created_at > datetime('now', '-5 minutes')",
                (tool_name,)
            )
            recent_errors = await cursor.fetchone()
        if recent_errors and recent_errors[0] >= 5:
            return False, (
                f"Tool '{tool_name}' has failed {recent_errors[0]} times in the last 5 minutes. "
                f"Consider switching strategy."
            )
    except Exception:
        pass
    
    return True, ""


async def get_error_frequency(minutes: int = 60, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most frequent error patterns in the last N minutes.
    Useful for proactive diagnostics and system health checks.
    """
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT normalized_pattern, tool_name, COUNT(*) as freq "
                "FROM error_logs "
                "WHERE created_at > datetime('now', ? || ' minutes') "
                "GROUP BY normalized_pattern, tool_name "
                "ORDER BY freq DESC LIMIT ?",
                (f"-{minutes}", limit)
            )
            rows = await cursor.fetchall()
        return [
            {"pattern": r[0], "tool": r[1], "count": r[2]}
            for r in rows
        ]
    except Exception:
        return []
