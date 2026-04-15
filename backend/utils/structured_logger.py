"""
Structured JSON Lines logger for agent execution.
Every tool call, plan, and decision is logged as machine-readable JSONL.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

LOG_FILE = os.environ.get("AGENT_LOG_FILE", "logs/agent_execution.jsonl")


def _ensure_log_dir():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log_event(event_type: str, data: Dict[str, Any],
              session_id: Optional[str] = None):
    """Write a structured log event to JSONL file."""
    try:
        _ensure_log_dir()
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session": session_id or "unknown",
            "type": event_type,
            **data
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write structured log: {e}")


def log_tool_call(session_id: str, tool_name: str,
                  params: Dict, result: Dict):
    log_event("tool_call", {
        "tool": tool_name,
        "params": params,
        "success": result.get("success", True),
        "error": result.get("error"),
        "output_len": len(str(result.get("output", "")))
    }, session_id)


def log_plan(session_id: str, plan: Dict, task: str):
    log_event("plan_created", {
        "task": task[:200],
        "strategy": plan.get("strategy"),
        "phases": len(plan.get("phases", []))
    }, session_id)


def log_json_repair(session_id: str, strategy_used: str,
                    raw_len: int, success: bool):
    log_event("json_repair", {
        "strategy": strategy_used,
        "raw_len": raw_len,
        "success": success
    }, session_id)


def log_model_response(session_id: str, model: str,
                       had_tool_call: bool, tokens: int):
    log_event("model_response", {
        "model": model,
        "had_tool_call": had_tool_call,
        "tokens": tokens
    }, session_id)
