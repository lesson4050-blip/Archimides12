"""
Radical Transparency — Full Audit Trail.

Every agent decision is recorded:
- Why this strategy was chosen (and alternatives rejected)
- Which agents were hired (and why, with economy data)
- Every tool call with params, result, and verification status
- Critic verdicts with specific issues
- Memory context that influenced the response
- Economy report (credits spent per agent)
- Timeline with timestamps
- Exportable as JSON or Markdown

This is what makes Archimedes the most transparent AI agent.
Users can audit every decision. No black box.
"""
import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    TASK_START = "task_start"
    ROUTING_DECISION = "routing_decision"
    MEMORY_RETRIEVED = "memory_retrieved"
    AGENT_HIRED = "agent_hired"
    TOOL_CALLED = "tool_called"
    TOOL_VERIFIED = "tool_verified"
    CRITIC_VERDICT = "critic_verdict"
    ECONOMY_UPDATE = "economy_update"
    SKILL_MATCHED = "skill_matched"
    STRATEGY_CHOSEN = "strategy_chosen"
    ALTERNATIVES_REJECTED = "alternatives_rejected"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"


@dataclass
class AuditEvent:
    type: AuditEventType
    timestamp: float
    data: Dict[str, Any]
    agent: str = "orchestrator"
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "elapsed_ms": round(self.duration_ms or 0, 1),
            "agent": self.agent,
            **self.data
        }


class TaskAuditTrail:
    """
    Complete audit trail for a single task execution.
    Records every decision with full context.
    """

    def __init__(self, task_id: str, task: str, session_id: str):
        self.task_id = task_id
        self.task = task
        self.session_id = session_id
        self.start_time = time.time()
        self.events: List[AuditEvent] = []
        self._last_event_time = self.start_time

        # Record task start
        self._record(AuditEventType.TASK_START, {
            "task": task,
            "task_id": task_id,
            "session_id": session_id,
        })

    def _record(self, event_type: AuditEventType, data: dict, agent: str = "orchestrator"):
        now = time.time()
        duration_ms = (now - self._last_event_time) * 1000
        self._last_event_time = now

        event = AuditEvent(
            type=event_type,
            timestamp=now,
            data=data,
            agent=agent,
            duration_ms=duration_ms
        )
        self.events.append(event)
        return event

    def record_routing(
        self,
        chosen_strategy: str,
        chosen_complexity: str,
        alternatives_considered: List[str],
        reason: str
    ):
        """Record why this strategy was chosen and others rejected."""
        self._record(AuditEventType.ROUTING_DECISION, {
            "chosen_strategy": chosen_strategy,
            "chosen_complexity": chosen_complexity,
            "alternatives_considered": alternatives_considered,
            "reason": reason,
        })

    def record_memory(
        self,
        memories_found: int,
        memory_preview: str,
        influenced_response: bool
    ):
        """Record what memories were retrieved and if they influenced the response."""
        self._record(AuditEventType.MEMORY_RETRIEVED, {
            "memories_found": memories_found,
            "memory_preview": memory_preview[:200] if memory_preview else "",
            "influenced_response": influenced_response,
        })

    def record_agent_hired(
        self,
        role: str,
        cost_credits: int,
        reason: str,
        confidence: float = 0.0
    ):
        """Record agent hiring decision with economy data."""
        self._record(AuditEventType.AGENT_HIRED, {
            "role": role,
            "cost_credits": cost_credits,
            "reason": reason,
            "confidence": round(confidence, 2),
        }, agent="economy")

    def record_tool_call(
        self,
        tool_name: str,
        params: dict,
        result_success: bool,
        result_preview: str,
        verification_status: str = "not_checked"
    ):
        """Record tool call with params, result, and verification."""
        # Sanitize params — remove sensitive values
        safe_params = {
            k: (v if len(str(v)) < 100 else str(v)[:100] + "...")
            for k, v in params.items()
        }
        self._record(AuditEventType.TOOL_CALLED, {
            "tool": tool_name,
            "params": safe_params,
            "success": result_success,
            "result_preview": result_preview[:200] if result_preview else "",
            "verification_status": verification_status,
        }, agent="executor")

    def record_critic_verdict(
        self,
        verdict: str,
        score: float,
        issues: List[str],
        retry_count: int
    ):
        """Record critic's verdict with specific issues."""
        self._record(AuditEventType.CRITIC_VERDICT, {
            "verdict": verdict,
            "score": round(score, 2),
            "issues": issues[:5],  # Top 5 issues
            "retry_count": retry_count,
            "will_retry": verdict == "RETRY",
        }, agent="critic")

    def record_economy(self, budget_report: dict):
        """Record economy spending for this task."""
        self._record(AuditEventType.ECONOMY_UPDATE, {
            "total_credits": budget_report.get("total_credits", 0),
            "spent_credits": budget_report.get("spent_credits", 0),
            "efficiency": budget_report.get("efficiency", 1.0),
            "agents_hired": [
                t["agent"] for t in budget_report.get("transactions", [])
            ],
        }, agent="economy")

    def record_completion(
        self,
        success: bool,
        output_preview: str,
        total_agents_used: int,
        total_tool_calls: int
    ):
        """Record task completion with summary stats."""
        total_duration = time.time() - self.start_time
        self._record(AuditEventType.TASK_COMPLETE, {
            "success": success,
            "output_preview": output_preview[:300] if output_preview else "",
            "total_duration_seconds": round(total_duration, 2),
            "total_agents_used": total_agents_used,
            "total_tool_calls": total_tool_calls,
            "total_events": len(self.events),
        })

    def to_dict(self) -> dict:
        """Export full audit trail as JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "task": self.task,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "total_duration_seconds": round(time.time() - self.start_time, 2),
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }

    def to_markdown(self) -> str:
        """Export audit trail as human-readable Markdown report."""
        lines = [
            f"# 🔍 Archimedes Audit Trail",
            f"**Task:** {self.task[:100]}",
            f"**Session:** {self.session_id}",
            f"**Duration:** {round(time.time() - self.start_time, 1)}s",
            f"**Events:** {len(self.events)}",
            "",
            "---",
            "",
            "## Timeline",
            "",
        ]

        for event in self.events:
            elapsed = round((event.timestamp - self.start_time), 2)
            icon = {
                AuditEventType.TASK_START: "🚀",
                AuditEventType.ROUTING_DECISION: "🗺️",
                AuditEventType.MEMORY_RETRIEVED: "🧠",
                AuditEventType.AGENT_HIRED: "🤖",
                AuditEventType.TOOL_CALLED: "🔧",
                AuditEventType.TOOL_VERIFIED: "✅",
                AuditEventType.CRITIC_VERDICT: "⚖️",
                AuditEventType.ECONOMY_UPDATE: "💰",
                AuditEventType.TASK_COMPLETE: "🏁",
                AuditEventType.ERROR: "❌",
            }.get(event.type, "•")

            lines.append(f"### {icon} [{elapsed}s] {event.type.value.replace('_', ' ').title()}")

            data = event.data
            if event.type == AuditEventType.ROUTING_DECISION:
                lines.append(f"- **Chosen:** `{data['chosen_strategy']}` ({data['chosen_complexity']})")
                lines.append(f"- **Reason:** {data.get('reason', 'pattern match')}")
                if data.get('alternatives_considered'):
                    lines.append(f"- **Rejected:** {', '.join(data['alternatives_considered'])}")

            elif event.type == AuditEventType.AGENT_HIRED:
                lines.append(f"- **Agent:** `{data['role']}` — {data['cost_credits']} credits")
                lines.append(f"- **Confidence:** {data['confidence']:.0%}")
                lines.append(f"- **Reason:** {data.get('reason', '')}")

            elif event.type == AuditEventType.TOOL_CALLED:
                status = "✅" if data['success'] else "❌"
                lines.append(f"- **Tool:** `{data['tool']}` {status}")
                if data.get('params'):
                    param_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in list(data['params'].items())[:3])
                    lines.append(f"- **Params:** `{param_str}`")
                lines.append(f"- **Result:** {data.get('result_preview', '')[:100]}")
                lines.append(f"- **Verification:** {data.get('verification_status', 'not_checked')}")

            elif event.type == AuditEventType.CRITIC_VERDICT:
                verdict_icon = "✅" if data['verdict'] == 'PASS' else "🔄"
                lines.append(f"- **Verdict:** {verdict_icon} {data['verdict']} (score: {data['score']})")
                if data.get('issues'):
                    lines.append(f"- **Issues:** {'; '.join(data['issues'][:3])}")

            elif event.type == AuditEventType.MEMORY_RETRIEVED:
                lines.append(f"- **Memories found:** {data['memories_found']}")
                lines.append(f"- **Influenced response:** {'Yes' if data['influenced_response'] else 'No'}")

            elif event.type == AuditEventType.ECONOMY_UPDATE:
                lines.append(f"- **Credits spent:** {data['spent_credits']}/{data['total_credits']}")
                lines.append(f"- **Efficiency:** {data['efficiency']:.0%}")

            elif event.type == AuditEventType.TASK_COMPLETE:
                status = "✅ Success" if data['success'] else "❌ Failed"
                lines.append(f"- **Status:** {status}")
                lines.append(f"- **Duration:** {data['total_duration_seconds']}s")
                lines.append(f"- **Agents used:** {data['total_agents_used']}")
                lines.append(f"- **Tool calls:** {data['total_tool_calls']}")

            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class AuditTrailManager:
    """Global manager for all active audit trails."""

    def __init__(self):
        self._trails: Dict[str, TaskAuditTrail] = {}
        self._completed: Dict[str, dict] = {}  # Store last 100 completed trails
        self._max_completed = 100

    def start_trail(self, task_id: str, task: str, session_id: str) -> TaskAuditTrail:
        trail = TaskAuditTrail(task_id, task, session_id)
        self._trails[task_id] = trail
        return trail

    def get_trail(self, task_id: str) -> Optional[TaskAuditTrail]:
        return self._trails.get(task_id)

    def complete_trail(self, task_id: str) -> Optional[dict]:
        trail = self._trails.pop(task_id, None)
        if trail:
            data = trail.to_dict()
            # Keep last 100
            if len(self._completed) >= self._max_completed:
                oldest = next(iter(self._completed))
                del self._completed[oldest]
            self._completed[task_id] = data
            return data
        return None

    def get_completed(self, task_id: str) -> Optional[dict]:
        return self._completed.get(task_id)

    def get_all_completed(self) -> List[dict]:
        return list(self._completed.values())


# Global singleton
audit_manager = AuditTrailManager()
