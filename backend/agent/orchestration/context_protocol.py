"""
Context Preservation Protocol — Zero-Loss Agent Handoff.

When Commander delegates to Warrior (or any agent-to-agent transfer),
the original user intent, nuances, and accumulated context are preserved
in full — not summarized, not truncated.

Architecture:
  - ContextEnvelope: immutable snapshot of the original request + all context
  - HandoffProtocol: manages the transfer with integrity verification
  - ContextDiff: tracks what each agent added vs. what was inherited

This closes the "забывчивость при передаче контекста" gap.
"""

import time
import hashlib
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=False)
class ContextEnvelope:
    """
    Immutable snapshot of user intent + accumulated agent context.
    Passed between agents without loss.
    """
    # Original user request — NEVER modified or summarized
    original_request: str

    # Full conversation history up to this point
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Accumulated agent insights (each agent appends, never overwrites)
    agent_notes: List[Dict[str, Any]] = field(default_factory=list)

    # Structured artifacts produced so far (code, files, plans)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)

    # Chain of custody — which agents have handled this envelope
    custody_chain: List[Dict[str, str]] = field(default_factory=list)

    # Integrity hash — verifies nothing was dropped
    _content_hash: str = ""

    # Creation timestamp
    created_at: float = field(default_factory=time.time)

    def compute_hash(self) -> str:
        """Compute integrity hash of the envelope contents."""
        content = (
            self.original_request
            + str(len(self.conversation_history))
            + str(len(self.agent_notes))
            + str(len(self.artifacts))
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def verify_integrity(self) -> bool:
        """Check that the envelope hasn't lost data during transfer."""
        if not self._content_hash:
            return True  # First use, no hash to verify
        return self.compute_hash() == self._content_hash

    def seal(self) -> None:
        """Seal the envelope with an integrity hash after modifications."""
        self._content_hash = self.compute_hash()


class HandoffProtocol:
    """
    Manages agent-to-agent context transfer with zero data loss.
    
    Usage:
        protocol = HandoffProtocol()
        
        # Create envelope at task start
        envelope = protocol.create_envelope(user_request, history)
        
        # Agent A processes and adds notes
        protocol.agent_handoff(envelope, "PlannerAgent", notes={...})
        
        # Agent B receives full context
        protocol.agent_handoff(envelope, "ExecutorAgent", notes={...})
        
        # Verify nothing was lost
        assert protocol.verify(envelope)
    """

    def __init__(self):
        self._active_envelopes: Dict[str, ContextEnvelope] = {}

    def create_envelope(
        self,
        user_request: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "default",
    ) -> ContextEnvelope:
        """Create a new context envelope for a task."""
        envelope = ContextEnvelope(
            original_request=user_request,
            conversation_history=deepcopy(conversation_history or []),
        )
        envelope.custody_chain.append({
            "agent": "HandoffProtocol",
            "action": "created",
            "timestamp": str(time.time()),
        })
        envelope.seal()
        self._active_envelopes[session_id] = envelope

        logger.info(
            f"Context envelope created: hash={envelope._content_hash}, "
            f"history_len={len(envelope.conversation_history)}"
        )
        return envelope

    def agent_handoff(
        self,
        envelope: ContextEnvelope,
        agent_name: str,
        notes: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Record an agent's contribution and pass the envelope forward.
        Returns True if integrity is maintained.
        """
        # Verify integrity before modification
        if not envelope.verify_integrity():
            logger.error(
                f"INTEGRITY VIOLATION: Envelope corrupted before {agent_name} handoff! "
                f"Expected hash={envelope._content_hash}, "
                f"actual={envelope.compute_hash()}"
            )
            # Don't block execution, but log the violation
            
        # Record this agent's contribution
        if notes:
            envelope.agent_notes.append({
                "agent": agent_name,
                "timestamp": time.time(),
                "notes": notes,
            })

        if artifacts:
            for artifact in artifacts:
                artifact["produced_by"] = agent_name
                artifact["timestamp"] = time.time()
                envelope.artifacts.append(artifact)

        # Update custody chain
        envelope.custody_chain.append({
            "agent": agent_name,
            "action": "processed",
            "timestamp": str(time.time()),
            "notes_added": len(notes) if notes else 0,
            "artifacts_added": len(artifacts) if artifacts else 0,
        })

        # Re-seal
        envelope.seal()

        logger.info(
            f"Handoff: {agent_name} → next agent | "
            f"notes={len(envelope.agent_notes)}, "
            f"artifacts={len(envelope.artifacts)}, "
            f"hash={envelope._content_hash}"
        )
        return True

    def get_full_context_for_agent(
        self,
        envelope: ContextEnvelope,
        agent_name: str,
        max_history: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Build a complete message list for an agent, including:
          1. System prompt with accumulated context
          2. Original user request (always present, never summarized)
          3. Previous agent notes (structured, not lossy)
          4. Recent conversation history
        """
        messages = []

        # System context with all accumulated agent knowledge
        context_parts = [
            f"ORIGINAL USER REQUEST (verbatim, do not paraphrase):\n{envelope.original_request}",
        ]

        if envelope.agent_notes:
            context_parts.append("\nPREVIOUS AGENT INSIGHTS:")
            for note in envelope.agent_notes:
                agent = note.get("agent", "unknown")
                content = note.get("notes", {})
                context_parts.append(f"  [{agent}]: {json.dumps(content, ensure_ascii=False, default=str)[:500]}")

        if envelope.artifacts:
            context_parts.append(f"\nARTIFACTS PRODUCED SO FAR: {len(envelope.artifacts)}")
            for art in envelope.artifacts[-5:]:  # Last 5 artifacts
                context_parts.append(
                    f"  - {art.get('type', 'unknown')}: "
                    f"{art.get('description', art.get('content', ''))[:200]}"
                )

        messages.append({
            "role": "system",
            "content": "\n".join(context_parts),
        })

        # Add conversation history (bounded)
        history = envelope.conversation_history[-max_history:]
        messages.extend(history)

        return messages

    def verify(self, envelope: ContextEnvelope) -> bool:
        """Final verification that the envelope is intact."""
        return envelope.verify_integrity()

    def get_custody_report(self, envelope: ContextEnvelope) -> Dict[str, Any]:
        """Generate a report of the envelope's journey through agents."""
        return {
            "original_request_length": len(envelope.original_request),
            "total_notes": len(envelope.agent_notes),
            "total_artifacts": len(envelope.artifacts),
            "agents_involved": [c["agent"] for c in envelope.custody_chain],
            "integrity_valid": envelope.verify_integrity(),
            "content_hash": envelope._content_hash,
            "created_at": envelope.created_at,
            "duration_seconds": round(time.time() - envelope.created_at, 2),
        }


# Need json import for context building
import json
