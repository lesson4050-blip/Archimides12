"""
Session Store v2 — SQLite-backed persistent state.

Replaces JSON file-per-session approach with a single SQLite database.
Survives process crashes, supports concurrent access, and enables
fast queries across all sessions.

Key improvements over v1 (JSON files):
- Atomic writes (no partial JSON corruption on crash)
- Single file instead of N files in a directory
- Indexed lookups by session_id and timestamp
- Built-in cleanup via SQL DELETE
- WAL mode for concurrent read/write
"""
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DB_PATH = Path("data/sessions.db")


def _ensure_db_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class SessionStore:
    """SQLite-backed session persistence with crash-safe atomic writes."""

    _local = threading.local()

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path or DB_PATH)
        _ensure_db_dir()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Thread-local connection (SQLite is not thread-safe by default)."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                task_desc    TEXT NOT NULL DEFAULT '',
                history      TEXT NOT NULL DEFAULT '[]',
                current_step INTEGER NOT NULL DEFAULT 0,
                metadata     TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL,
                version      INTEGER NOT NULL DEFAULT 2
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                step_name    TEXT NOT NULL,
                state        TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(updated_at);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_session
                ON checkpoints(session_id, created_at DESC);
        """)
        conn.commit()

    # ─── Session CRUD ────────────────────────────────────────────

    def save_context(
        self,
        session_id: str,
        history: list,
        task_description: str,
        current_step: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Upsert session context. Atomic — safe against crashes."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO sessions (session_id, task_desc, history, current_step, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    task_desc    = excluded.task_desc,
                    history      = excluded.history,
                    current_step = excluded.current_step,
                    metadata     = excluded.metadata,
                    updated_at   = excluded.updated_at
                """,
                (
                    session_id,
                    task_description,
                    json.dumps(history, default=str),
                    current_step,
                    json.dumps(metadata or {}, default=str),
                    now,
                    now,
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"SessionStore save failed: {e}")
            return False

    def load_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session context."""
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            data = {
                "session_id": row["session_id"],
                "task_description": row["task_desc"],
                "history": json.loads(row["history"]),
                "current_step": row["current_step"],
                "metadata": json.loads(row["metadata"]),
                "saved_at": row["updated_at"],
                "version": row["version"],
            }
            logger.info(f"Restored session {session_id} from {data['saved_at']}")
            return data
        except Exception as e:
            logger.error(f"SessionStore load failed: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session (cascades to checkpoints)."""
        try:
            conn = self._get_conn()
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"SessionStore delete failed: {e}")
            return False

    # ─── Checkpoints ─────────────────────────────────────────────

    def save_checkpoint(self, session_id: str, step_name: str, state: dict) -> bool:
        """Save a step checkpoint. Keeps last 10 per session."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO checkpoints (session_id, step_name, state, created_at) VALUES (?, ?, ?, ?)",
                (session_id, step_name, json.dumps(state, default=str), now),
            )
            # Prune old checkpoints (keep last 10)
            conn.execute(
                """
                DELETE FROM checkpoints
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM checkpoints
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT 10
                )
                """,
                (session_id, session_id),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Checkpoint save failed: {e}")
            return False

    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the most recent checkpoint for a session."""
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "step": row["step_name"],
                "state": json.loads(row["state"]),
                "time": row["created_at"],
            }
        except Exception as e:
            logger.error(f"Checkpoint load failed: {e}")
            return None

    # ─── Queries ─────────────────────────────────────────────────

    def list_active_sessions(self) -> List[str]:
        """List all active session IDs."""
        try:
            conn = self._get_conn()
            rows = conn.execute("SELECT session_id FROM sessions ORDER BY updated_at DESC").fetchall()
            return [r["session_id"] for r in rows]
        except Exception:
            return []

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        try:
            conn = self._get_conn()
            cutoff = datetime.fromtimestamp(
                time.time() - (max_age_hours * 3600), tz=timezone.utc
            ).isoformat()
            conn.execute("PRAGMA foreign_keys = ON")
            result = conn.execute(
                "DELETE FROM sessions WHERE updated_at < ?", (cutoff,)
            )
            conn.commit()
            if result.rowcount:
                logger.info(f"Cleaned up {result.rowcount} stale sessions (>{max_age_hours}h)")
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Database statistics for monitoring."""
        try:
            conn = self._get_conn()
            sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
            checkpoints = conn.execute("SELECT COUNT(*) as c FROM checkpoints").fetchone()["c"]
            db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            return {
                "sessions": sessions,
                "checkpoints": checkpoints,
                "db_size_bytes": db_size,
                "db_size_mb": round(db_size / (1024 * 1024), 2),
            }
        except Exception:
            return {}


# ─── Migration from v1 (JSON files) ─────────────────────────────

def migrate_from_json(json_dir: str = "data/sessions", store: Optional[SessionStore] = None):
    """One-time migration: import existing JSON session files into SQLite."""
    json_path = Path(json_dir)
    if not json_path.exists():
        return 0

    store = store or SessionStore()
    migrated = 0

    for f in json_path.glob("*.json"):
        if f.name.endswith("_checkpoint.json"):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            store.save_context(
                session_id=data.get("session_id", f.stem),
                history=data.get("history", []),
                task_description=data.get("task_description", ""),
                current_step=data.get("current_step", 0),
                metadata=data.get("metadata", {}),
            )
            # Migrate checkpoint if exists
            cp_path = json_path / f"{f.stem}_checkpoint.json"
            if cp_path.exists():
                with open(cp_path, "r", encoding="utf-8") as fh:
                    cp = json.load(fh)
                store.save_checkpoint(
                    session_id=f.stem,
                    step_name=cp.get("step", "unknown"),
                    state=cp.get("state", {}),
                )
            migrated += 1
        except Exception as e:
            logger.warning(f"Failed to migrate {f.name}: {e}")

    if migrated:
        logger.info(f"Migrated {migrated} sessions from JSON to SQLite")
    return migrated


# ─── Global singleton ────────────────────────────────────────────

_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
        # Auto-migrate from v1 on first access
        try:
            migrate_from_json(store=_store)
        except Exception as e:
            logger.warning(f"Migration from JSON failed (non-critical): {e}")
    return _store
