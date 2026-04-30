"""
Session Memory — Per-session markdown notes maintained automatically.

Runs in background after every N tool calls:
1. Scans recent conversation for key information
2. Extracts: decisions, errors, files modified, current status
3. Writes to data/session_memory/{session_id}.md
4. On new session, loads relevant memories from past sessions

Distinct from consolidator.py (long-term semantic extraction)
and memory_bank.py (factual knowledge store).
Session memory is short-term, session-specific, markdown-formatted.
"""
import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SESSION_MEMORY_DIR = os.environ.get("SESSION_MEMORY_DIR", "data/session_memory")
EXTRACTION_INTERVAL = 10
MAX_MEMORY_SIZE = 4000


class SessionMemory:
    """Maintains a running markdown summary of the current session."""

    def __init__(self, session_id: str, router=None):
        self.session_id = session_id
        self.router = router
        self._tool_call_count = 0
        self._last_extraction_at = 0
        self._memory_path = os.path.join(SESSION_MEMORY_DIR, f"{session_id}.md")
        self._current_memory = ""
        self._extraction_lock = asyncio.Lock()
        os.makedirs(SESSION_MEMORY_DIR, exist_ok=True)

    async def on_tool_call(self, tool_name: str, result: Dict[str, Any], messages: List[Dict]):
        """Called after each tool call. Triggers extraction if threshold met."""
        self._tool_call_count += 1
        if self._tool_call_count - self._last_extraction_at >= EXTRACTION_INTERVAL:
            asyncio.create_task(self._extract_and_save(messages))

    async def _extract_and_save(self, messages: List[Dict]):
        """Extract key information and save to file."""
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
            self._current_memory = header + memory_text
            tmp_path = self._memory_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(self._current_memory[:MAX_MEMORY_SIZE])
            os.replace(tmp_path, self._memory_path)
            logger.debug(f"Session memory updated: {len(self._current_memory)} chars")

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

    def load(self) -> str:
        """Load existing session memory."""
        try:
            if os.path.exists(self._memory_path):
                with open(self._memory_path) as f:
                    self._current_memory = f.read()
        except Exception:
            pass
        return self._current_memory

    @staticmethod
    def search_past_sessions(query: str, top_k: int = 5) -> list:
        """Search across ALL past session memories for relevant context."""
        results = []
        memory_dir = Path(SESSION_MEMORY_DIR)
        if not memory_dir.exists():
            return results

        query_terms = set(query.lower().split())

        for memory_file in memory_dir.glob("*.md"):
            try:
                content = memory_file.read_text()
                content_lower = content.lower()
                score = sum(1 for term in query_terms if term in content_lower)
                if score > 0:
                    results.append({
                        "session_id": memory_file.stem,
                        "score": score,
                        "preview": content[:300],
                        "file": str(memory_file),
                    })
            except Exception:
                continue

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def list_recent_sessions(limit: int = 10) -> list:
        """List most recent session memories."""
        memory_dir = Path(SESSION_MEMORY_DIR)
        if not memory_dir.exists():
            return []
        files = sorted(
            memory_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime, reverse=True
        )
        results = []
        for f in files[:limit]:
            try:
                content = f.read_text()
                results.append({
                    "session_id": f.stem,
                    "preview": content[:200],
                    "modified": f.stat().st_mtime,
                })
            except Exception:
                continue
        return results

    @property
    def current_memory(self) -> str:
        return self._current_memory
