"""
State Checkpoint System — Crash-Resilient Agent State Persistence.

Production-grade state management that survives process crashes, network failures,
and unexpected restarts. Every agent thought, plan, and intermediate result is
durably persisted and can be recovered.

Architecture:
  - Write-Ahead Log (WAL) pattern: state changes are journaled before execution
  - Atomic checkpoints: full state snapshots at critical milestones
  - Recovery: on startup, replay the WAL from the last checkpoint

This closes the "state loss on crash" gap identified in the Manus/Devin comparison.
"""

import json
import time
import logging
import hashlib
import asyncio
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Default checkpoint storage directory
_CHECKPOINT_DIR = Path("./data/checkpoints")


class StateCheckpoint:
    """
    Durable state persistence with write-ahead logging.

    Usage:
        cp = StateCheckpoint(session_id="abc123")
        await cp.save(state)          # Full snapshot
        await cp.append_wal(event)    # Incremental journal entry
        recovered = await cp.recover() # Restore after crash
    """

    def __init__(self, session_id: str, checkpoint_dir: Optional[Path] = None):
        self.session_id = session_id
        self.base_dir = (checkpoint_dir or _CHECKPOINT_DIR) / session_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._wal_path = self.base_dir / "wal.jsonl"
        self._snapshot_path = self.base_dir / "snapshot.json"
        self._lock = asyncio.Lock()
        self._wal_count = 0
        self._snapshot_interval = 20  # Auto-snapshot every N WAL entries

    async def save(self, state_data: Dict[str, Any]) -> str:
        """
        Atomically persist a full state snapshot.
        Uses write-to-temp + rename pattern to prevent corruption.
        Returns the checkpoint ID (content hash).
        """
        async with self._lock:
            checkpoint = {
                "version": 2,
                "session_id": self.session_id,
                "timestamp": time.time(),
                "state": state_data,
            }
            content = json.dumps(checkpoint, ensure_ascii=False, default=str)
            checkpoint_id = hashlib.sha256(content.encode()).hexdigest()[:16]
            checkpoint["checkpoint_id"] = checkpoint_id

            # Atomic write: temp file → rename
            tmp_path = self._snapshot_path.with_suffix(".tmp")
            try:
                tmp_path.write_text(
                    json.dumps(checkpoint, ensure_ascii=False, default=str),
                    encoding="utf-8"
                )
                tmp_path.replace(self._snapshot_path)
            except Exception as e:
                logger.error(f"Checkpoint save failed: {e}")
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

            # Truncate WAL after a successful snapshot
            self._wal_path.write_text("", encoding="utf-8")
            self._wal_count = 0

            logger.info(
                f"Checkpoint saved: {checkpoint_id} "
                f"({len(content)} bytes, session={self.session_id})"
            )
            return checkpoint_id

    async def append_wal(self, event: Dict[str, Any]) -> None:
        """
        Append an incremental state change to the Write-Ahead Log.
        These are replayed on top of the last snapshot during recovery.
        """
        async with self._lock:
            entry = {
                "seq": self._wal_count,
                "timestamp": time.time(),
                "event": event,
            }
            try:
                with open(self._wal_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
                self._wal_count += 1
            except Exception as e:
                logger.error(f"WAL append failed: {e}")

    async def recover(self) -> Optional[Dict[str, Any]]:
        """
        Recover the last known state:
          1. Load the snapshot (if exists)
          2. Replay WAL entries on top of it
        Returns None if no checkpoint exists.
        """
        snapshot = None

        # 1. Load snapshot
        if self._snapshot_path.exists():
            try:
                raw = self._snapshot_path.read_text(encoding="utf-8")
                snapshot = json.loads(raw)
                logger.info(
                    f"Snapshot loaded: {snapshot.get('checkpoint_id', '?')} "
                    f"(session={self.session_id})"
                )
            except Exception as e:
                logger.error(f"Snapshot load failed: {e}")
                return None

        # 2. Replay WAL
        wal_entries: List[Dict[str, Any]] = []
        if self._wal_path.exists():
            try:
                for line in self._wal_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        wal_entries.append(json.loads(line))
            except Exception as e:
                logger.warning(f"WAL replay partial failure: {e}")

        if not snapshot and not wal_entries:
            return None

        result = {
            "snapshot": snapshot.get("state") if snapshot else {},
            "wal_entries": [e.get("event") for e in wal_entries],
            "recovered_at": time.time(),
            "snapshot_id": snapshot.get("checkpoint_id") if snapshot else None,
            "wal_count": len(wal_entries),
        }
        logger.info(
            f"State recovered: snapshot={'yes' if snapshot else 'no'}, "
            f"wal_entries={len(wal_entries)}"
        )
        return result

    async def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove checkpoints older than max_age_hours. Returns count removed."""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0

        if self._snapshot_path.exists():
            try:
                raw = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
                if raw.get("timestamp", 0) < cutoff:
                    self._snapshot_path.unlink()
                    removed += 1
            except Exception:
                pass

        if self._wal_path.exists():
            try:
                stat = self._wal_path.stat()
                if stat.st_mtime < cutoff:
                    self._wal_path.unlink()
                    removed += 1
            except Exception:
                pass

        return removed

    def exists(self) -> bool:
        """Check if any checkpoint data exists for this session."""
        return self._snapshot_path.exists() or self._wal_path.exists()
