"""
Archimedes learns from failures. Every time a tool call fails
or TDD cycle fails, it stores the fix pattern.
Next time it sees similar code, it proactively avoids the mistake.
"""
import sqlite3
import os
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("SELF_IMPROVE_DB", "data/self_improvement.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_pattern TEXT NOT NULL,
            fix_pattern TEXT NOT NULL,
            tool_name TEXT,
            success_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def learn_from_error(error: str, fix: str, tool_name: str = ""):
    """Store a fix pattern when agent successfully recovers."""
    try:
        # Normalize error to pattern (remove line numbers, paths)
        pattern = re.sub(r'\d+', 'N', error[:200])
        pattern = re.sub(r'/[^\s]+', '/PATH', pattern)

        conn = _get_conn()
        # Check if pattern already exists
        existing = conn.execute(
            "SELECT id FROM lessons WHERE error_pattern = ?",
            (pattern,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE lessons SET success_count = success_count + 1 "
                "WHERE error_pattern = ?",
                (pattern,)
            )
        else:
            conn.execute(
                "INSERT INTO lessons "
                "(error_pattern, fix_pattern, tool_name) VALUES (?,?,?)",
                (pattern, fix[:500], tool_name)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Self-improvement learn failed: {e}")


def get_fix_hint(error: str) -> Optional[str]:
    """Get a previously learned fix for similar error."""
    try:
        pattern = re.sub(r'\d+', 'N', error[:200])
        pattern = re.sub(r'/[^\s]+', '/PATH', pattern)

        conn = _get_conn()
        row = conn.execute(
            "SELECT fix_pattern FROM lessons "
            "WHERE error_pattern = ? "
            "ORDER BY success_count DESC LIMIT 1",
            (pattern,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
