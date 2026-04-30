"""
Session Memory — Per-session notes maintained automatically.

Architecture upgrade: SQLite backend (was: file-based markdown).
Uses aiosqlite for async access, consistent with memory_bank.py.

Runs in background after every N tool calls:
1. Scans recent conversation for key information
2. Extracts: decisions, errors, files modified, current status
3. Stores in SQLite (data/session_memory.db)
4. On new session, loads relevant memories from past sessions

Distinct from consolidator.py (long-term semantic extraction)
and memory_bank.py (factual knowledge store).
Session memory is short-term, session-specific.
"""
import asyncio
import hashlib
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Legacy file dir (read-only, for migration)
SESSION_MEMORY_DIR = os.environ.get("SESSION_MEMORY_DIR", "data/session_memory")

# New SQLite path
SESSION_MEMORY_DB = os.environ.get("SESSION_MEMORY_DB", "data/session_memory.db")

EXTRACTION_INTERVAL = 10
MAX_MEMORY_SIZE = 4000


def _ensure_db() -> str:
    """Ensure the SQLite database and table exist. Returns db path."""
    os.makedirs(os.path.dirname(SESSION_MEMORY_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(SESSION_MEMORY_DB)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_memory (
                session_id   TEXT PRIMARY KEY,
                content      TEXT NOT NULL DEFAULT '',
                current_task TEXT NOT NULL DEFAULT '',
                updated_at   TEXT NOT NULL,
                tool_calls   INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_updated
            ON session_memory(updated_at DESC)
        """)
        conn.commit()
    finally:
        conn.close()
    return SESSION_MEMORY_DB


class SessionMemory:
    """Maintains a running summary of the current session (SQLite-backed)."""

    def __init__(self, session_id: str, router=None):
        self.session_id = session_id
        self.router = router
        self._tool_call_count = 0
        self._last_extraction_at = 0
        self._current_memory = ""
        self._extraction_lock = asyncio.Lock()
        self._db_path = _ensure_db()

    # ── Public API ───────────────────────────────────────────────

    async def on_tool_call(self, tool_name: str, result: Dict[str, Any], messages: List[Dict]):
        """Called after each tool call. Triggers extraction if threshold met."""
        self._tool_call_count += 1
        if self._tool_call_count - self._last_extraction_at >= EXTRACTION_INTERVAL:
            asyncio.create_task(self._extract_and_save(messages))

    def load(self) -> str:
        """Load existing session memory from SQLite."""
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                row = conn.execute(
                    "SELECT content FROM session_memory WHERE session_id = ?",
                    (self.session_id,)
                ).fetchone()
                if row:
                    self._current_memory = row[0]
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"Session memory load failed: {e}")
            # Fallback: try legacy file
            self._load_legacy_file()
        return self._current_memory

    @property
    def current_memory(self) -> str:
        return self._current_memory

    # ── Extraction ───────────────────────────────────────────────

    async def _extract_and_save(self, messages: List[Dict]):
        """Extract key information and save to SQLite."""
        async with self._extraction_lock:
            self._last_extraction_at = self._tool_call_count
            recent = messages[-30:]
            extracted = self._extract_key_info(recent)
            if not extracted:
                return

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            header = f"# Session Memory: {self.session_id}\n_Last updated: {timestamp}_\n\n"

            if self.router:
                try:
                    memory_text = await self._llm_extract(recent)
                except Exception:
                    memory_text = extracted
            else:
                memory_text = extracted

            self._current_memory = (header + memory_text)[:MAX_MEMORY_SIZE]

            # Derive current_task from extraction
            current_task = ""
            for msg in recent:
                if msg.get("role") == "user":
                    current_task = str(msg.get("content", ""))[:200]
                    break

            self._save_to_db(current_task, timestamp)
            logger.debug(f"Session memory updated: {len(self._current_memory)} chars")

    def _save_to_db(self, current_task: str, timestamp: str):
        """Write session memory to SQLite (upsert)."""
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO session_memory (session_id, content, current_task, updated_at, tool_calls)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        content = excluded.content,
                        current_task = excluded.current_task,
                        updated_at = excluded.updated_at,
                        tool_calls = excluded.tool_calls
                    """,
                    (self.session_id, self._current_memory, current_task,
                     timestamp, self._tool_call_count),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Session memory save failed: {e}")

    def _extract_key_info(self, messages: List[Dict]) -> str:
        """Extract key information without LLM (fast, extractive)."""
        sections: Dict[str, Any] = {
            "errors": [], "files_modified": [], "decisions": [],
            "current_task": "", "tools_used": set(),
        }
        for msg in messages:
            content = str(msg.get("content", ""))
            role = msg.get("role", "")
            for line in content.split("\n"):
                if any(kw in line.lower() for kw in ["error:", "exception:", "traceback", "failed"]):
                    sections["errors"].append(line.strip()[:150])
            file_patterns = re.findall(r'(?:backend|frontend|tests)/[\w/]+\.(?:py|ts|tsx)', content)
            sections["files_modified"].extend(file_patterns)
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {}).get("name", "")
                    if fn:
                        sections["tools_used"].add(fn)
            if role == "user" and not sections["current_task"]:
                sections["current_task"] = content[:200]
        parts = []
        if sections["current_task"]:
            parts.append(f"## Current Task\n{sections['current_task']}\n")
        if sections["files_modified"]:
            unique_files = list(set(sections["files_modified"]))[:20]
            parts.append("## Files Modified\n" + "\n".join(f"- `{f}`" for f in unique_files) + "\n")
        if sections["errors"]:
            unique_errors = list(set(sections["errors"]))[:10]
            parts.append("## Errors Encountered\n" + "\n".join(f"- {e}" for e in unique_errors) + "\n")
        if sections["tools_used"]:
            parts.append("## Tools Used\n" + ", ".join(sorted(sections["tools_used"])) + "\n")
        return "\n".join(parts)

    async def _llm_extract(self, messages: List[Dict]) -> str:
        """Use LLM for smart memory extraction."""
        conversation = ""
        for msg in messages[-15:]:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:200]
            conversation += f"[{role}]: {content}\n"
        resp = await self.router.generate(
            messages=[{"role": "user", "content": f"Extract key information from this conversation as markdown. Include: current task, files modified, errors encountered, decisions made. Be concise (max 500 chars).\n\n{conversation}"}],
            task_hint="quick"
        )
        return resp.get("text", "")[:2000]

    # ── Legacy file migration ────────────────────────────────────

    def _load_legacy_file(self):
        """Load from old file-based storage (backward compat)."""
        legacy_path = os.path.join(SESSION_MEMORY_DIR, f"{self.session_id}.md")
        try:
            if os.path.exists(legacy_path):
                with open(legacy_path) as f:
                    self._current_memory = f.read()
                # Migrate to SQLite
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                self._save_to_db("", timestamp)
                logger.info(f"Migrated session {self.session_id} from file to SQLite")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")

    # ── Static query methods ─────────────────────────────────────

    @staticmethod
    def search_past_sessions(query: str, top_k: int = 5) -> list:
        """Search across ALL past session memories for relevant context."""
        results = []
        try:
            db_path = _ensure_db()
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT session_id, content FROM session_memory"
                ).fetchall()
            finally:
                conn.close()

            query_terms = set(query.lower().split())
            for session_id, content in rows:
                content_lower = content.lower()
                score = sum(1 for term in query_terms if term in content_lower)
                if score > 0:
                    results.append({
                        "session_id": session_id,
                        "score": score,
                        "preview": content[:300],
                    })

            results.sort(key=lambda r: r["score"], reverse=True)
        except Exception as e:
            logger.debug(f"Session search failed: {e}")
        return results[:top_k]

    @staticmethod
    def list_recent_sessions(limit: int = 10) -> list:
        """List most recent session memories."""
        results = []
        try:
            db_path = _ensure_db()
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT session_id, content, updated_at FROM session_memory "
                    "ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            finally:
                conn.close()

            for session_id, content, updated_at in rows:
                results.append({
                    "session_id": session_id,
                    "preview": content[:200],
                    "modified": updated_at,
                })
        except Exception as e:
            logger.debug(f"Session list failed: {e}")
        return results
