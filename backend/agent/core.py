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

    def __init__(self, 
                 router: 'ModelRouter',
                 tool_registry: 'ToolRegistry',
                 context_manager: 'ContextManager',
                 vector_store: 'VectorStore',
                 orchestrator: 'AgentOrchestrator',
                 mcp_client: 'ArchimedesMCPClient',
                 connector_bridge: 'ConnectorMCPBridge',
                 subconscious: 'SubconsciousEngine',
                 name: str = "ArchimedesCosmo", 
                 session_id: Optional[str] = None, 
                 max_retries: int = 3):
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
        
        # Injected Dependencies
        self.router = router
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.vector_store = vector_store
        self.orchestrator = orchestrator
        self.mcp_client = mcp_client
        self.connector_bridge = connector_bridge
        self.subconscious = subconscious
        
        self.system_prompt: str = ThoughtEngine.get_system_prompt()
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        
        from backend.agent.tool_definition_cache import ToolDefinitionCache
        self._tool_def_cache: ToolDefinitionCache = ToolDefinitionCache(self)

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
        try:
            await self._init_mcp()
            await self._init_connectors()
        except Exception as e:
            logger.error(f"Async initialization failed: {e}")
        finally:
            self.tool_registry.set_ready()

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
            
            # Optimization: only wait if there are actually servers to connect to
            if not getattr(self.mcp_client, "servers_config", {}):
                return

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
        
        # Wait for tools to be ready
        await self.tool_registry.wait_until_ready()
        
        try:
            self.state = AgentState.PLANNING if mode == AgentMode.PLANNING else AgentState.EXECUTING
            if websocket_send:
                await websocket_send({"type": "message_info", "content": f"🚀 Mode: **{mode.value.upper()}** — {task_description}"})
            
            # Save periodic context checkpoint
            try:
                from backend.agent.session_store import get_session_store
                await asyncio.to_thread(
                    get_session_store().save_context,
                    session_id=self.session_id or "default",
                    history=self.context_manager.get_messages()[:10],
                    task_description=task_description,
                    metadata={"mode": mode.value}
                )
            except (ImportError, IOError) as e:
                logger.warning(f"Context checkpoint unavailable: {e}")
            except Exception as e:
                logger.warning(f"Context checkpoint failed ({type(e).__name__}): {e}")
            
            # Inject persistent memory context
            memory_context = ""
            try:
                from backend.memory.memory_router import MemoryRouter
                if not hasattr(self, '_memory_router'):
                    self._memory_router = MemoryRouter(
                        user_id=getattr(self, 'user_id', 'default'),
                        session_id=self.session_id
                    )
                memory_context = await asyncio.wait_for(
                    self._memory_router.get_context_string(task_description, max_tokens=1500),
                    timeout=3.0
                )
            except Exception as e:
                logger.debug(f"Memory context fetch failed (non-critical): {e}")
          
            # Prepend memory to task if we have relevant context
            enriched_task = task_description
            if memory_context:
                enriched_task = (
                    f"[MEMORY CONTEXT - use this to personalize your response]\n"
                    f"{memory_context}\n"
                    f"[END MEMORY CONTEXT]\n\n"
                    f"CURRENT TASK: {task_description}"
                )
                logger.info(f"Memory injected: ~{len(memory_context.split())} tokens")

            orch_result = await self.orchestrator.run_task(
                task_description=enriched_task, 
                mode=mode,
                session_id=self.session_id or "default", 
                websocket_send=websocket_send,
                task_hint=kwargs.get("task_hint", "default"), 
                stream=stream
            )
            
            if not orch_result.get("success"):
                raise Exception(orch_result.get("error", "Orchestrator failed"))
                
            final_output = orch_result.get("output", "Task completed.")
            
            # Save conversation turns for multi-turn memory
            self.context_manager.add_message("user", task_description)
            self.context_manager.add_message("assistant", str(final_output) if final_output else "")
            
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
            
            # Store successful task in episodic memory
            if result.status == TaskStatus.COMPLETED and memory_context is not None:
                try:
                    output_text = str(getattr(result, 'output', ''))[:1000]
                    await asyncio.wait_for(
                        self._memory_router.store(
                            task=task_description,
                            result=output_text,
                            memory_type="episodic",
                            metadata={
                                "strategy": getattr(result, 'metadata', {}).get('strategy', 'unknown'),
                                "duration": getattr(result, 'duration', 0),
                            }
                        ),
                        timeout=5.0
                    )
                    logger.info("Task experience stored in episodic memory")
                except Exception as e:
                    logger.debug(f"Memory store failed (non-critical): {e}")
            
            # Record to flywheel for continuous learning
            try:
                from backend.agent.flywheel import flywheel
                flywheel.record_session(
                    session_id=self.session_id or "default",
                    task=task_description,
                    result={
                        "success": getattr(result, 'status', None) == TaskStatus.COMPLETED,
                        "strategy": getattr(result, 'metadata', {}).get('strategy', 'unknown'),
                        "output": str(getattr(result, 'output', ''))[:500],
                        "error": getattr(result, 'error', None),
                    },
                    history=self.context_manager.get_messages()[-10:] if hasattr(self, 'context_manager') else []
                )
            except Exception as e:
                logger.debug(f"Flywheel record failed (non-critical): {e}")

            # Trigger subconscious predictive analysis in background
            try:
                from backend.utils.task import safe_create_task
                output_text = str(getattr(result, 'output', ''))
                if output_text and len(output_text) > 50:
                    safe_create_task(
                        self.subconscious.trigger_predictive_analysis(
                            current_thought=task_description[:200],
                            session_id=self.session_id or "default"
                        )
                    )
            except Exception as e:
                logger.debug(f"Subconscious trigger failed (non-critical): {e}")

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
            
            # Extract user preferences from this conversation
            try:
                from backend.memory.preference_extractor import PreferenceExtractor
                from backend.memory.vector_store import VectorStore
                vs = VectorStore(user_id=getattr(self, 'user_id', 'default'))
                extractor = PreferenceExtractor(vs)
                prefs = await asyncio.wait_for(
                    extractor.extract_and_store(self.context_manager.get_messages()[-10:]),
                    timeout=3.0
                )
                if prefs:
                    logger.info(f"Stored {len(prefs)} user preferences")
            except Exception as e:
                logger.debug(f"Preference extraction failed (non-critical): {e}")
            
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