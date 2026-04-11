from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
import logging
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract Base Class for specialized agents in the Archimedes Orchestration system.
    """
    def __init__(self, name: str, router: ModelRouter):
        self.name = name
        self.router = router

    @abstractmethod
    async def process(self, state: OrchestrationState, websocket_send: Optional[Callable] = None) -> OrchestrationState:
        """
        Primary entry point for agent logic. 
        Args:
            state: The current global orchestration state.
            websocket_send: Optional callback for real-time UI updates.
        Returns:
            The potentially modified orchestration state.
        """
        pass

    async def log_thought(self, content: str, websocket_send: Optional[Callable] = None):
        """Standardized logging for agent internal thoughts."""
        logger.info(f"[{self.name}] THOUGHT: {content}")
        if websocket_send:
            # We keep the labeling "Archimedes" in the UI as per user request, 
            # but we can include the agent name in the payload if needed.
            await websocket_send({
                "type": "thought", 
                "content": content,
                "agent": self.name 
            })

    async def log_info(self, content: str, websocket_send: Optional[Callable] = None):
        """Standardized logging for agent status updates."""
        logger.info(f"[{self.name}] INFO: {content}")
        if websocket_send:
            await websocket_send({
                "type": "message_info", 
                "content": content
            })
