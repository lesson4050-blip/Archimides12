"""
Archimedes Agent Core — Slim orchestration hub.
Extracted: tool_initializer.py, task_processor.py, tool_definition_cache.py
"""
from backend.utils.task import safe_create_task
import asyncio, logging, datetime, uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from backend.models.model_router import ModelRouter
from backend.agent.thought_engine import ThoughtEngine
from backend.agent.tool_registry import ToolRegistry
from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.agent.orchestration.state import AgentMode
from backend.config import settings

logger = logging.getLogger(__name__)
class TaskStatus(str, Enum):
    """Represents the current lifecycle state of a task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentState(str, Enum):
    """Internal state machine for the Archimedes agent."""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """
    Data container for the result of a task execution.
    
    Attributes:
        task_id (str): Unique identifier for the task.
        status (TaskStatus): Final outcome status.
        output (Any, optional): Data produced by the task.
        error (str, optional): Error message if task failed.
        duration (float): Time taken to execute in seconds.
        timestamp (str): ISO format execution time.
        metadata (Dict[str, Any]): Additional context (mode, plan, etc.).
    """
    task_id: str
    status: TaskStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the result to a dictionary."""
        return asdict(self)


@dataclass
class TaskPlan:
    """
    Represent a structured plan for complex task execution.
    
    Attributes:
        task_id (str): Unique identifier for the planned task.
        description (str): Human-readable task description.
        subtasks (List[Dict]): List of atomic subtask definitions.
        strategy (str): Execution strategy (e.g., sequential, parallel).
        priority (int): Task priority level (1-5).
        estimated_duration (float): Estimated time in seconds.
        created_at (str): ISO format creation time.
    """
    task_id: str
    description: str
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = "sequential"
    priority: int = 1
    estimated_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the plan to a dictionary."""
        return asdict(self)


class ArchimedesCosmoAgent:
    """
    The main cognitive hub and orchestration engine for Archimedes.
    
    This class manages the agent's state, tools, model routing, and task processing.
    It integrates with MCP (Model Context Protocol) for dynamic tool discovery and 
    orchestrates sub-agents through specialized execution strategies.
    
    Args:
        name (str): Agent display name.
        session_id (str, optional): Unique ID for user session persistence.
        max_retries (int): Maximum number of retries for failed tool calls.
    """

    def __init__(self, name: str = "ArchimedesCosmo", session_id: Optional[str] = None, max_retries: int = 3):
        self.agent_id: str = str(uuid.uuid4())
        self.session_id: Optional[str] = session_id
        self.name: str = name
        self.max_retries: int = max_retries
        self.state: AgentState = AgentState.IDLE
        self.tasks: Dict[str, TaskPlan] = {}
        from collections import deque
        self.results: Dict[str, ExecutionResult] = {}
        self.execution_history: deque = deque(maxlen=500)
        self.memory: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.error_handlers: Dict[str, Callable] = {}
        self.router: ModelRouter = ModelRouter()
        self.system_prompt: str = ThoughtEngine.get_system_prompt()
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

        from backend.memory.context_manager import ContextManager
        from backend.memory.vector_store import VectorStore
        self.context_manager: ContextManager = ContextManager(max_tokens=getattr(settings, 'AGENT_MAX_CONTEXT_TOKENS', 32768))
        self.vector_store: VectorStore = VectorStore(user_id=session_id or "default")

        # FIX 7: tool_registry is single source of truth; self.tools is a property
        self.tool_registry: ToolRegistry = ToolRegistry()
        self.orchestrator: AgentOrchestrator = AgentOrchestrator(
            router=self.router, 
            tool_registry=self.tool_registry, 
            context_manager=self.context_manager
        )

        from backend.mcp_hub.client import ArchimedesMCPClient
        self.mcp_client: ArchimedesMCPClient = ArchimedesMCPClient(getattr(settings, "MCP_EXTERNAL_SERVERS", {}))
        self.orchestrator._mcp_client_ref = self.mcp_client
        
        from backend.connectors.mcp_bridge import ConnectorMCPBridge
        self.connector_bridge: ConnectorMCPBridge = ConnectorMCPBridge(self.tool_registry, self.session_id or "default")
        
        from backend.agent.tool_definition_cache import ToolDefinitionCache
        self._tool_def_cache: ToolDefinitionCache = ToolDefinitionCache(self)
        
        from backend.agent.tool_initializer import ToolInitializer
        ToolInitializer(self.tool_registry, self.session_id, self).initialize_all()

        for msg in self.history:
            self.context_manager.add_message(msg["role"], msg.get("content", ""))
        logger.info(f"OK: Initialized {self.name} (ID: {self.agent_id})")

        # Schedule async initialization (MCP + connectors) without blocking __init__
        safe_create_task(self.initialize())

        # Schedule nightly memory consolidation
        from backend.memory.consolidator import MemoryConsolidator
        safe_create_task(
            MemoryConsolidator.schedule_nightly(self.router, interval_hours=12)
        )

    @property
    def tools(self) -> Dict[str, Callable]:
        """Delegates to tool_registry. Returns a mapping of tool names to their handler functions."""
        return self.tool_registry.tools

    async def initialize(self) -> None:
        """Performs asynchronous initialization including MCP connection and connector syncing."""
        await self._init_mcp()
        await self._init_connectors()

    async def _init_connectors(self) -> None:
        """Synchronizes connected services and updates system prompt with connector context."""
        try:
            await self.connector_bridge.sync_connected_services()
            ctx = self.connector_bridge.get_active_services_context()
            if ctx:
                self.system_prompt += f"\n\n{ctx}"
                if self.history and self.history[0].get("role") == "system":
                    self.history[0]["content"] = self.system_prompt
                logger.info("Connector bridge initialized")
        except Exception as e:
            logger.warning(f"Connector init failed (non-critical): {e}")

    async def _init_mcp(self) -> None:
        """Discover and register tools from external MCP servers using event-based polling."""
        try:
            await self.mcp_client.connect_all()
            MAX_WAIT, POLL_INTERVAL, elapsed = 10.0, 0.5, 0.0
            mcp_tools = []
            while elapsed < MAX_WAIT:
                mcp_tools = await self.mcp_client.discover_tools()
                if mcp_tools:
                    break
                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL
            
            for tool_def in mcp_tools:
                sn = tool_def["function"]["_mcp_server"]
                tn = tool_def["function"]["_mcp_tool_name"]
                async def cb(s=sn, t=tn, **p): return await self.mcp_client.call_external_tool(s, t, p)
                self.tool_registry.register_mcp_tool(tool_def, cb)
            
            if mcp_tools:
                logger.info(f"MCP: registered {len(mcp_tools)} tools")
        except Exception as e:
            logger.error(f"MCP init failed: {e}")

    async def sync_mcp_tools(self) -> None:
        """Force a manual synchronization of MCP tools to discover new servers or functions."""
        try:
            mcp_tools = await self.mcp_client.discover_tools()
            count = 0
            for tool_def in mcp_tools:
                name = tool_def["function"]["name"]
                if name not in self.tool_registry.tools:
                    sn = tool_def["function"]["_mcp_server"]
                    tn = tool_def["function"]["_mcp_tool_name"]
                    async def cb(s=sn, t=tn, **p): return await self.mcp_client.call_external_tool(s, t, p)
                    self.tool_registry.register_mcp_tool(tool_def, cb)
                    count += 1
            if count:
                logger.info(f"MCP sync: {count} new tools")
        except Exception as e:
            logger.error(f"MCP sync failed: {e}")

    async def process_task(self, task_description: str, websocket_send: Optional[Callable] = None,
                           stream: bool = False, **kwargs) -> ExecutionResult:
        """
        Main entry point for task execution. Handles planning, orchestration, and output streaming.
        
        Args:
            task_description (str): The natural language request from the user.
            websocket_send (Callable, optional): Function to stream intermediate results.
            stream (bool): Whether to stream agent's internal thoughts.
            **kwargs: Additional options like 'mode' (FAST/PLANNING) or 'task_hint'.
            
        Returns:
            ExecutionResult: The final outcome of the task.
        """
        task_id = str(uuid.uuid4())
        start_time = asyncio.get_running_loop().time()
        mode = AgentMode.FAST if kwargs.get("mode", "planning").lower() == "fast" else AgentMode.PLANNING
        
        try:
            self.state = AgentState.PLANNING if mode == AgentMode.PLANNING else AgentState.EXECUTING
            if websocket_send:
                await websocket_send({"type": "message_info", "content": f"🚀 Mode: **{mode.value.upper()}** — {task_description}"})
            
            # Save periodic context checkpoint
            try:
                from backend.agent.session_store import get_session_store
                get_session_store().save_context(
                    session_id=self.session_id or "default",
                    history=self.context_manager.get_messages()[:10],
                    task_description=task_description,
                    metadata={"mode": mode.value}
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
            
            orch_result = await self.orchestrator.run_task(
                task_description=task_description, 
                mode=mode,
                session_id=self.session_id or "default", 
                websocket_send=websocket_send,
                task_hint=kwargs.get("task_hint", "default"), 
                stream=stream
            )
            
            if not orch_result.get("success"):
                raise Exception(orch_result.get("error", "Orchestrator failed"))
                
            final_output = orch_result.get("output", "Task completed.")
            if websocket_send and final_output:
                await websocket_send({"type": "message_result", "content": str(final_output)})
                
            self.state = AgentState.COMPLETED
            result = ExecutionResult(
                task_id=task_id, 
                status=TaskStatus.COMPLETED, 
                output=final_output,
                duration=asyncio.get_running_loop().time() - start_time,
                metadata={"mode": mode.value, "plan": orch_result.get("plan")}
            )
            
            # Record performance metrics
            from backend.utils.metrics import metrics
            from backend.utils.task import safe_create_task
            safe_create_task(metrics.record_task(
                session_id=self.session_id or "default",
                task_description=task_description,
                success=(result.status == TaskStatus.COMPLETED),
                duration_s=result.duration,
                mode=mode.value,
            ))
            
            # Session lifecycle management should handle deletions, not task completion.
                
        except Exception as e:
            logger.error(f"Task failed: {e}")
            if websocket_send:
                await websocket_send({"type": "agent_error", "content": f"Error: {e}"})
            self.state = AgentState.ERROR
            result = ExecutionResult(
                task_id=task_id, 
                status=TaskStatus.FAILED, 
                error=str(e),
                duration=asyncio.get_running_loop().time() - start_time
            )
            
        self.results[task_id] = result
        self.execution_history.append(result)
        return result

    def register_tool(self, name: str, handler: Callable) -> None:
        """
        Registers a new tool handler and invalidates the tool definition cache.
        
        Args:
            name (str): The name of the tool as recognized by the LLM.
            handler (Callable): The function to execute when the tool is called.
        """
        self.tool_registry.register(name, handler)
        self._tool_def_cache.invalidate()
        logger.info(f"TOOL registered: {name}")

    def register_error_handler(self, error_type: str, handler: Callable) -> None:
        """Registers a custom handler for specific error types."""
        self.error_handlers[error_type] = handler

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates performance statistics from the execution history."""
        completed = sum(1 for r in self.execution_history if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in self.execution_history if r.status == TaskStatus.FAILED)
        total = len(self.execution_history)
        total_dur = sum(r.duration for r in self.execution_history)
        return {
            "agent_id": self.agent_id, 
            "name": self.name, 
            "total_tasks": total,
            "completed": completed, 
            "failed": failed,
            "success_rate": (completed / total * 100) if total else 0,
            "total_duration": total_dur, 
            "average_duration": total_dur / total if total else 0,
            "registered_tools": len(self.tools)
        }

    async def get_status(self) -> Dict[str, Any]:
        """Returns the current state and high-level activity metrics of the agent."""
        return {
            "agent_id": self.agent_id, 
            "name": self.name, 
            "state": self.state.value,
            "active_tasks": len([t for t in self.tasks.values() if t.task_id not in self.results]),
            "completed_tasks": len([r for r in self.results.values() if r.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([r for r in self.results.values() if r.status == TaskStatus.FAILED]),
            "memory_size": len(self.memory), 
            "statistics": self.get_statistics()
        }