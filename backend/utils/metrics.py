"""
Lightweight metrics collector for Archimedes.
Tracks task outcomes, tool usage, model performance.
Used for self-improvement loops and benchmark reporting.
"""
import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

METRICS_FILE = Path("/tmp/archimedes_metrics.jsonl")


class MetricsCollector:
    """Collect and persist agent performance metrics."""
    
    _instance = None
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    @classmethod
    def get(cls) -> "MetricsCollector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def record_task(
        self,
        session_id: str,
        task_description: str,
        success: bool,
        duration_s: float,
        mode: str,
        tool_count: int = 0,
        model_used: str = "unknown"
    ):
        """Record a completed task outcome."""
        async with self._lock:
            event = {
                "event": "task_complete",
                "ts": datetime.now().isoformat(),
                "session_id": session_id,
                "task_preview": task_description[:100],
                "success": success,
                "duration_s": round(duration_s, 2),
                "mode": mode,
                "tool_count": tool_count,
                "model": model_used,
            }
            self._append_event(event)
            
            self._counters["tasks_total"] += 1
            self._counters["tasks_success" if success else "tasks_failed"] += 1
            self._timers["task_duration"].append(duration_s)
    
    async def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        session_id: str = "unknown"
    ):
        """Record a tool call outcome."""
        async with self._lock:
            self._counters[f"tool_{tool_name}_total"] += 1
            if not success:
                self._counters[f"tool_{tool_name}_errors"] += 1
            self._timers[f"tool_{tool_name}_ms"].append(duration_ms)
    
    async def record_model_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        success: bool
    ):
        """Record a model API call."""
        async with self._lock:
            event = {
                "event": "model_call",
                "ts": datetime.now().isoformat(),
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": round(latency_ms, 1),
                "success": success,
            }
            self._append_event(event)
            self._counters[f"model_{model}_calls"] += 1
            self._counters[f"model_{model}_tokens"] += tokens_in + tokens_out
    
    def get_summary(self) -> Dict[str, Any]:
        """Return current metrics summary."""
        total = self._counters.get("tasks_total", 0)
        success = self._counters.get("tasks_success", 0)
        durations = self._timers.get("task_duration", [])
        
        return {
            "tasks_total": total,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
            "tool_stats": {
                k: v for k, v in self._counters.items()
                if k.startswith("tool_")
            },
            "model_stats": {
                k: v for k, v in self._counters.items()
                if k.startswith("model_")
            },
        }
    
    @staticmethod
    def _append_event(event: Dict[str, Any]):
        """Append event to JSONL file."""
        try:
            with open(METRICS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.debug(f"Metrics write failed (non-critical): {e}")


metrics = MetricsCollector.get()
