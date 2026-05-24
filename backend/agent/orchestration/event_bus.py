"""
Streaming Event Bus — Real-Time Agent Visibility Layer.

Every agent thought, tool call, plan step, and decision is emitted as a
structured event to all connected consumers (WebSocket, SSE, logging).

Event Categories:
  - thought:     Agent's internal reasoning (chain-of-thought)
  - tool_call:   Tool invocation with arguments
  - tool_result: Tool execution result
  - plan:        Plan created or updated
  - progress:    Step completion, progress percentage
  - token:       Raw LLM token for streaming display
  - error:       Error or warning
  - checkpoint:  State checkpoint saved
  - security:    Security gate decision

This closes the "user sees result only when agent finishes" gap
and brings UX to Manus-level real-time visibility.
"""

import time
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All possible event types in the streaming pipeline."""
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PLAN = "plan_update"
    PLAN_STEP = "plan_step"
    PROGRESS = "progress"
    TOKEN = "token"
    ERROR = "agent_error"
    WARNING = "warning"
    CHECKPOINT = "checkpoint"
    SECURITY = "security"
    HANDOFF = "handoff"
    METRIC = "metric"
    STATUS = "status"
    DONE = "done"
    BROWSER_NAVIGATE = "browser_navigate"


@dataclass
class StreamEvent:
    """A single event in the streaming pipeline."""
    type: EventType
    content: Any
    agent: str = "orchestrator"
    session_id: str = "default"
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "agent": self.agent,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "seq": self.sequence,
            "metadata": self.metadata,
        }


class EventBus:
    """
    Central event bus for real-time agent visibility.
    
    Supports multiple consumers:
      - WebSocket callback (real-time UI)
      - SSE queue (HTTP streaming)
      - Audit log (forensic replay)
    
    Usage:
        bus = EventBus(session_id="abc")
        bus.add_consumer(websocket_send)
        
        await bus.emit_thought("Analyzing the codebase structure...")
        await bus.emit_tool_call("shell", {"command": "ls -la"})
        await bus.emit_progress(step=3, total=5, description="Running tests")
    """

    _instances: Dict[str, 'EventBus'] = {}
    
    @classmethod
    def get_instance(cls, session_id: str) -> 'EventBus':
        """Get or create a singleton EventBus for a specific session."""
        if session_id not in cls._instances:
            cls._instances[session_id] = cls(session_id)
        return cls._instances[session_id]

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self._consumers: List[Callable] = []
        self._sequence = 0
        self._event_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000
        self._filters: Set[EventType] = set()  # Empty = no filter (all events pass)

    def add_consumer(self, callback: Callable) -> None:
        """Register a consumer (WebSocket send, SSE queue, etc.)."""
        if callback and callback not in self._consumers:
            self._consumers.append(callback)

    def subscribe(self, callback: Callable) -> None:
        """Alias for add_consumer."""
        self.add_consumer(callback)

    def remove_consumer(self, callback: Callable) -> None:
        """Unregister a consumer."""
        self._consumers = [c for c in self._consumers if c is not callback]

    def unsubscribe(self, callback: Callable) -> None:
        """Alias for remove_consumer."""
        self.remove_consumer(callback)

    def set_filter(self, event_types: Set[EventType]) -> None:
        """Only emit events of these types. Empty set = all events."""
        self._filters = event_types

    async def emit(self, event: StreamEvent) -> None:
        """Emit an event to all consumers."""
        event.sequence = self._sequence
        event.session_id = self.session_id
        self._sequence += 1

        # Apply filter
        if self._filters and event.type not in self._filters:
            return

        event_dict = event.to_dict()

        # Log for audit
        self._event_log.append(event_dict)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size // 2:]

        # Dispatch to all consumers
        for consumer in self._consumers:
            try:
                result = consumer(event_dict)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"Event consumer error: {e}")

    # ── Convenience emitters ────────────────────────────────────────

    async def emit_thought(self, thought: str, agent: str = "orchestrator") -> None:
        """Emit an agent's reasoning step."""
        await self.emit(StreamEvent(
            type=EventType.THOUGHT,
            content=thought,
            agent=agent,
        ))

    async def emit_tool_call(
        self, tool_name: str, arguments: Dict[str, Any], agent: str = "executor"
    ) -> None:
        """Emit a tool invocation event."""
        await self.emit(StreamEvent(
            type=EventType.TOOL_CALL,
            content={"tool": tool_name, "arguments": arguments},
            agent=agent,
        ))

    async def emit_tool_result(
        self, tool_name: str, result: Any, success: bool = True, agent: str = "executor"
    ) -> None:
        """Emit a tool execution result."""
        await self.emit(StreamEvent(
            type=EventType.TOOL_RESULT,
            content={
                "tool": tool_name,
                "result": str(result)[:2000],  # Truncate large results
                "success": success,
            },
            agent=agent,
        ))

    async def emit_plan(self, plan: Dict[str, Any], agent: str = "planner") -> None:
        """Emit a plan creation/update event."""
        await self.emit(StreamEvent(
            type=EventType.PLAN,
            content=plan,
            agent=agent,
        ))

    async def emit_progress(
        self, step: int, total: int, description: str = "", agent: str = "orchestrator"
    ) -> None:
        """Emit a progress update."""
        pct = round((step / max(1, total)) * 100)
        await self.emit(StreamEvent(
            type=EventType.PROGRESS,
            content={
                "step": step,
                "total": total,
                "percentage": pct,
                "description": description,
            },
            agent=agent,
        ))

    async def emit_token(self, token: str, agent: str = "executor") -> None:
        """Emit a raw LLM token for streaming display."""
        await self.emit(StreamEvent(
            type=EventType.TOKEN,
            content=token,
            agent=agent,
        ))

    async def emit_error(self, error: str, agent: str = "orchestrator") -> None:
        """Emit an error event."""
        await self.emit(StreamEvent(
            type=EventType.ERROR,
            content=error,
            agent=agent,
        ))

    async def emit_handoff(
        self, from_agent: str, to_agent: str, context_summary: str = ""
    ) -> None:
        """Emit an agent handoff event."""
        await self.emit(StreamEvent(
            type=EventType.HANDOFF,
            content={
                "from": from_agent,
                "to": to_agent,
                "context": context_summary,
            },
            agent=from_agent,
        ))

    async def emit_security(
        self, verdict: Dict[str, Any], agent: str = "security_gate"
    ) -> None:
        """Emit a security gate decision."""
        await self.emit(StreamEvent(
            type=EventType.SECURITY,
            content=verdict,
            agent=agent,
        ))

    async def emit_checkpoint(self, checkpoint_id: str, agent: str = "orchestrator") -> None:
        """Emit a state checkpoint event."""
        await self.emit(StreamEvent(
            type=EventType.CHECKPOINT,
            content={"checkpoint_id": checkpoint_id},
            agent=agent,
        ))

    async def emit_done(self, result_summary: str = "", agent: str = "orchestrator") -> None:
        """Emit task completion."""
        await self.emit(StreamEvent(
            type=EventType.DONE,
            content=result_summary,
            agent=agent,
        ))

    # ── Query / Replay ──────────────────────────────────────────────

    def get_event_log(self, last_n: int = 50) -> List[Dict[str, Any]]:
        """Return recent events for replay or debugging."""
        return self._event_log[-last_n:]

    def get_stats(self) -> Dict[str, Any]:
        """Return event bus statistics."""
        type_counts: Dict[str, int] = {}
        for event in self._event_log:
            t = event.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_events": self._sequence,
            "consumers": len(self._consumers),
            "log_size": len(self._event_log),
            "event_types": type_counts,
        }
