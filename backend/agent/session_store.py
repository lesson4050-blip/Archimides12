"""
Session Store — persist agent state across restarts.
Allows long-running tasks to survive server crashes/restarts.
"""
import asyncio
import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SESSION_DIR = Path("/tmp/archimedes_sessions")


class SessionStore:
    """Persist and restore agent session state."""

    def __init__(self):
        SESSION_DIR.mkdir(exist_ok=True)

    def save_context(
        self,
        session_id: str,
        history: list,
        task_description: str,
        current_step: int = 0,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Save session context to disk."""
        try:
            session_data = {
                "session_id": session_id,
                "history": history,
                "task_description": task_description,
                "current_step": current_step,
                "metadata": metadata or {},
                "saved_at": datetime.now().isoformat(),
                "version": 2
            }
            path = SESSION_DIR / f"{session_id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"SessionStore save failed: {e}")
            return False

    def load_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session context from disk."""
        try:
            path = SESSION_DIR / f"{session_id}.json"
            if not path.exists():
                return None
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Restored session {session_id} from {data['saved_at']}")
            return data
        except Exception as e:
            logger.error(f"SessionStore load failed: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session after successful completion."""
        try:
            path = SESSION_DIR / f"{session_id}.json"
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            logger.error(f"SessionStore delete failed: {e}")
            return False

    def list_active_sessions(self) -> list:
        """List all active (saved) session IDs."""
        try:
            return [f.stem for f in SESSION_DIR.glob("*.json")]
        except Exception:
            return []

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        import time
        cutoff = time.time() - (max_age_hours * 3600)
        for path in SESSION_DIR.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                logger.info(f"Cleaned up stale session: {path.stem}")


# Global singleton
_store = SessionStore()


def get_session_store() -> SessionStore:
    return _store
