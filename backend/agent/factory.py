import uuid
import logging
from typing import Optional
from backend.config import settings
from backend.models.model_router import ModelRouter
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager
from backend.memory.vector_store import VectorStore
from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.mcp_hub.client import ArchimedesMCPClient
from backend.connectors.mcp_bridge import ConnectorMCPBridge
from backend.agent.subconscious import SubconsciousEngine
from backend.agent.core import ArchimedesCosmoAgent
from backend.agent.tool_initializer import ToolInitializer

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating fully-wired ArchimedesCosmoAgent instances.
    Implements Dependency Injection to keep the AgentCore thin and testable.
    """
    @staticmethod
    def create(name: str = "ArchimedesCosmo", session_id: Optional[str] = None, max_retries: int = 3) -> ArchimedesCosmoAgent:
        # 1. Core Services
        router = ModelRouter()
        tool_registry = ToolRegistry()
        context_manager = ContextManager(max_tokens=getattr(settings, 'AGENT_MAX_CONTEXT_TOKENS', 32768))
        vector_store = VectorStore(user_id=session_id or "default")
        
        # 2. External Integration
        mcp_client = ArchimedesMCPClient(getattr(settings, "MCP_EXTERNAL_SERVERS", {}))
        connector_bridge = ConnectorMCPBridge(tool_registry, session_id or "default")
        
        # 3. Execution Engines
        orchestrator = AgentOrchestrator(
            router=router, 
            tool_registry=tool_registry, 
            context_manager=context_manager,
            session_id=session_id or "default"
        )
        orchestrator._mcp_client_ref = mcp_client
        
        subconscious = SubconsciousEngine(router, tool_registry)
        
        # 4. Assemble the Agent
        agent = ArchimedesCosmoAgent(
            router=router,
            tool_registry=tool_registry,
            context_manager=context_manager,
            vector_store=vector_store,
            orchestrator=orchestrator,
            mcp_client=mcp_client,
            connector_bridge=connector_bridge,
            subconscious=subconscious,
            name=name,
            session_id=session_id,
            max_retries=max_retries
        )
        
        # 5. Initialize Tools
        ToolInitializer(tool_registry, session_id, agent).initialize_all()
        
        logger.info(f"AgentFactory: Successfully wired {name} (ID: {agent.agent_id})")
        return agent
