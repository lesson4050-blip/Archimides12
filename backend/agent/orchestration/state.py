from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid
import datetime

class AgentMode(str, Enum):
    FAST = "fast"
    PLANNING = "planning"

@dataclass
class OrchestrationState:
    """
    Global Workspace for Multi-Agent Orchestration.
    Holds shared state between Planner, Executor, and Critic agents.
    """
    session_id: str
    task_description: str
    mode: AgentMode = AgentMode.PLANNING
    
    # State tracking
    history: List[Dict[str, Any]] = field(default_factory=list)
    current_plan: Optional[Dict[str, Any]] = None
    current_step_index: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Critic retry tracking
    critic_retry_limit: int = 3
    current_retry_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def add_message(self, role: str, content: str, **kwargs):
        """Append a message to the shared history."""
        msg = {"role": role, "content": content, **kwargs}
        self.history.append(msg)
        self.updated_at = datetime.datetime.now().isoformat()

    def get_context_manager_data(self) -> List[Dict[str, Any]]:
        """Extract history for ContextManager sync."""
        return self.history
