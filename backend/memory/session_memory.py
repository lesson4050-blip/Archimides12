import logging
import sqlite3
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
SESSION_MEMORY_DB = os.environ.get(\"SESSION_MEMORY_DB\", \"data/session_memory.db\")

class SessionMemory:
    def __init__(self, session_id: str, router=None):
        self.session_id = session_id
        self.router = router
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(SESSION_MEMORY_DB) or \".\", exist_ok=True)
        conn = sqlite3.connect(SESSION_MEMORY_DB)
        conn.execute(\"CREATE TABLE IF NOT EXISTS session_memory (session_id TEXT PRIMARY KEY, content TEXT, current_task TEXT, updated_at TEXT, tool_calls INTEGER)\")
        conn.commit()
        conn.close()

    def load(self) -> str:
        conn = sqlite3.connect(SESSION_MEMORY_DB)
        row = conn.execute(\"SELECT content FROM session_memory WHERE session_id = ?\", (self.session_id,)).fetchone()
        conn.close()
        return row[0] if row else \"\"

    def _save_to_db(self, content: str, task: str):
        conn = sqlite3.connect(SESSION_MEMORY_DB)
        conn.execute(\"INSERT OR REPLACE INTO session_memory VALUES (?, ?, ?, ?, ?)\", 
                     (self.session_id, content, task, datetime.now(timezone.utc).isoformat(), 0))
        conn.commit()
        conn.close()
