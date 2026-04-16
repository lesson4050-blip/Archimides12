"""
Memory Bank: persistent cross-session knowledge storage.
Agents write facts, rules, and summaries here.
On each new session, relevant memories are loaded automatically.
"""
import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("MEMORY_BANK_DB", "data/memory_bank.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            fact TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def save_fact(fact: str, session_id: str = "global",
              category: str = "general", importance: int = 1):
    """Save a fact to the memory bank."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO memories "
            "(session_id, fact, category, importance, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, fact[:2000], category, importance,
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        logger.info(f"Memory Bank: saved fact (category={category})")
    except Exception as e:
        logger.error(f"Memory Bank save error: {e}")


def get_relevant_facts(
    query: str = "",
    limit: int = 5,
    category: Optional[str] = None
) -> List[str]:
    """Retrieve most relevant/important facts."""
    try:
        conn = _get_conn()
        if category:
            rows = conn.execute(
                "SELECT fact FROM memories "
                "WHERE category = ? "
                "ORDER BY importance DESC, access_count DESC "
                "LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT fact FROM memories "
                "ORDER BY importance DESC, access_count DESC "
                "LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Memory Bank retrieve error: {e}")
        return []


def get_session_summary(session_id: str) -> str:
    """Get a text summary of what was learned in a session."""
    facts = []
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT fact FROM memories WHERE session_id = ? "
            "ORDER BY importance DESC LIMIT 10",
            (session_id,)
        ).fetchall()
        conn.close()
        facts = [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Memory Bank session summary error: {e}")
    if not facts:
        return ""
    return "Known facts from memory:\n" + "\n".join(
        f"• {f}" for f in facts
    )
