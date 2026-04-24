"""
Memory Bank: persistent cross-session knowledge storage.
Agents write facts, rules, and summaries here.
On each new session, relevant memories are loaded automatically.
"""
import logging
import os
import aiosqlite
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("MEMORY_BANK_DB", "data/memory_bank.db")


async def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
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
        await conn.commit()


async def save_fact(fact: str, session_id: str = "global",
              category: str = "general", importance: int = 1):
    """Save a fact to the memory bank."""
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as conn:
            await conn.execute(
                "INSERT INTO memories "
                "(session_id, fact, category, importance, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, fact[:2000], category, importance,
                 datetime.utcnow().isoformat())
            )
            await conn.commit()
        logger.info(f"Memory Bank: saved fact (category={category})")
    except Exception as e:
        logger.error(f"Memory Bank save error: {e}")


async def get_relevant_facts(
    query: str = "",
    limit: int = 5,
    category: Optional[str] = None
) -> List[str]:
    """Retrieve most relevant/important facts."""
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as conn:
            if query:
                # Simple keyword search - split query and match
                keywords = query.lower().split()[:5]
                conditions = " OR ".join(
                    [f"LOWER(fact) LIKE ?" for _ in keywords]
                )
                params = [f"%{kw}%" for kw in keywords]
                if category:
                    conditions += " AND category = ?"
                    params.append(category)
                params.append(limit)
                cursor = await conn.execute(
                    f"SELECT fact FROM memories WHERE ({conditions}) "
                    f"ORDER BY importance DESC LIMIT ?",
                    params
                )
                rows = await cursor.fetchall()
                # No results for keyword search
                if not rows:
                    return []
            else:
                if category:
                    cursor = await conn.execute(
                        "SELECT fact FROM memories "
                        "WHERE category = ? "
                        "ORDER BY importance DESC, access_count DESC "
                        "LIMIT ?",
                        (category, limit)
                    )
                    rows = await cursor.fetchall()
                else:
                    cursor = await conn.execute(
                        "SELECT fact FROM memories "
                        "ORDER BY importance DESC, access_count DESC "
                        "LIMIT ?",
                        (limit,)
                    )
                    rows = await cursor.fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Memory Bank retrieve error: {e}")
        return []


async def get_session_summary(session_id: str) -> str:
    """Get a text summary of what was learned in a session."""
    facts = []
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute(
                "SELECT fact FROM memories WHERE session_id = ? "
                "ORDER BY importance DESC LIMIT 10",
                (session_id,)
            )
            rows = await cursor.fetchall()
        facts = [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Memory Bank session summary error: {e}")
    if not facts:
        return ""
    return "Known facts from memory:\n" + "\n".join(
        f"• {f}" for f in facts
    )
