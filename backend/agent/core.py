"""
КОСМО-уровневое ядро агента Archimedes.
Полностью переработанная архитектура с максимальной надежностью и производительностью.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import datetime
import os
import uuid

from backend.models.model_router import ModelRouter
from backend.agent.thought_engine import ThoughtEngine
from backend.agent.tool_registry import ToolRegistry
from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.agent.orchestration.state import AgentMode
from backend.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Статус задачи."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentState(str, Enum):
    """Состояние агента."""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """Результат выполнения задачи."""
    task_id: str
    status: TaskStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    """План выполнения задачи."""
    task_id: str
    description: str
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = "sequential"  # sequential, parallel, adaptive
    priority: int = 1
    estimated_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArchimedesCosmoAgent:
    """
    КОСМО-уровневый агент Archimedes.
    
    Характеристики:
    - Надежное выполнение задач с автоматическим восстановлением
    - Интеллектуальное планирование и оптимизация
    - Управление памятью и контекстом
    - Параллельное выполнение задач
    - Полное логирование и аналитика
    """

    def __init__(self, name: str = "ArchimedesCosmo", session_id: str = None, max_retries: int = 3):
        self.agent_id = str(uuid.uuid4())
        self.session_id = session_id
        self.name = name
        self.max_retries = max_retries
        self.state = AgentState.IDLE
        
        # Управление задачами
        self.tasks: Dict[str, TaskPlan] = {}
        self.results: Dict[str, ExecutionResult] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # Память и контекст
        self.memory: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        
        # Инструменты и обработчики
        self.tools: Dict[str, Callable] = {}
        self.error_handlers: Dict[str, Callable] = {}
        
        # Интеллектуальный роутер и промпты
        self.router = ModelRouter()
        self.system_prompt = ThoughtEngine.get_system_prompt()
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        
        # Memory and context
        from backend.memory.context_manager import ContextManager
        from backend.memory.vector_store import VectorStore
        
        self.context_manager = ContextManager(
            max_tokens=settings.AGENT_MAX_CONTEXT_TOKENS if hasattr(settings, 'AGENT_MAX_CONTEXT_TOKENS') else 32768
        )
        self.vector_store = VectorStore(user_id=session_id or "default")
        
        # New: Tool Registry and Orchestrator
        self.tool_registry = ToolRegistry()
        self.orchestrator = AgentOrchestrator(
            router=self.router,
            tool_registry=self.tool_registry,
            context_manager=self.context_manager
        )
        
        # MCP Integration: Initialize and connect external servers
        from backend.mcp_hub.client import ArchimedesMCPClient
        self.mcp_client = ArchimedesMCPClient(getattr(settings, "MCP_EXTERNAL_SERVERS", {}))
        # asyncio.create_task(self._init_mcp())  # Moved to initialize()

        # Connector Bridge: Nango OAuth + MCP tool registration
        from backend.connectors.mcp_bridge import ConnectorMCPBridge
        self.connector_bridge = ConnectorMCPBridge(
            self.tool_registry,
            self.session_id or "default"
        )

        # Registration of extended tools
        self._init_extended_tools()
        
        # Sync initial history
        # self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]  # REMOVED: defined twice
        for msg in self.history:
            self.context_manager.add_message(msg["role"], msg.get("content", ""))
            
        logger.info(f"OK: Инициализирован {self.name} (ID: {self.agent_id})")

    async def initialize(self):
        """Async initialization for the agent."""
        await self._init_mcp()
        await self._init_connectors()

    async def _init_connectors(self):
        """Initialize connector bridge — load connected services as agent tools."""
        try:
            await self.connector_bridge.sync_connected_services()
            ctx = self.connector_bridge.get_active_services_context()
            if ctx:
                # Inject into system prompt so the agent knows what's available
                self.system_prompt = self.system_prompt + f"\n\n{ctx}"
                if self.history and self.history[0].get("role") == "system":
                    self.history[0]["content"] = self.system_prompt
                logger.info("Connector bridge initialized with active services")
        except Exception as e:
            logger.warning(f"Connector init failed (non-critical): {e}")

    def _init_extended_tools(self):
        """Инициализация и регистрация всех доступных инструментов."""
        try:
            from .tools.pdf_tool import PDFTool
            from .tools.image_gen_tool import ImageGenTool
            from .tools.github_tool import GithubTool
            from .tools.email_tool import EmailTool
            from .tools.utility_tools import VideoTool, AudioTool, SheetsTool
            from backend.tools.schedule_tool import ScheduleTool
            
            # Core tools from backend.tools
            from backend.tools.file_tool import FileTool
            from backend.tools.search_tool import SearchTool
            from backend.tools.shell_tool import ShellTool
            from backend.tools.browser_tool import BrowserTool
            from backend.sandbox.singleton import sandbox_manager

            # Инстанцирование и регистрация
            self.browser_tool = BrowserTool(sandbox_manager.executor)
            self.register_tool("browser", self.browser_tool.execute)
            
            self.pdf_tool = PDFTool()
            self.register_tool("pdf", self.pdf_tool.execute)
            
            self.image_gen_tool = ImageGenTool()
            self.register_tool("image_gen", self.image_gen_tool.execute)
            
            self.github_tool = GithubTool()
            self.register_tool("github", self.github_tool.execute)
            
            self.email_tool = EmailTool()
            self.register_tool("email", self.email_tool.execute)
            
            self.video_tool = VideoTool()
            self.register_tool("video", self.video_tool.execute)
            
            self.audio_tool = AudioTool()
            self.register_tool("audio", self.audio_tool.execute)
            
            self.sheets_tool = SheetsTool()
            self.register_tool("sheets", self.sheets_tool.execute)
            
            self.schedule_tool = ScheduleTool()
            self.register_tool("schedule", self.schedule_tool.execute)
            
            # Phase 2: Trigger Tool
            from backend.tools.trigger_tool import TriggerTool
            self.trigger_tool = TriggerTool()
            self.register_tool("trigger", self.trigger_tool.execute)
            
            # Phase 1: Voice Tool
            from backend.tools.voice_tool import VoiceTool
            self.voice_tool = VoiceTool()
            self.register_tool("voice", self.voice_tool.execute)
            
            # Phase 1: Monitor Tool
            from backend.tools.monitor_tool import MonitorTool
            self.monitor_tool = MonitorTool()
            self.register_tool("monitor", self.monitor_tool.execute)
            
            # Phase 1: Document Tool
            from backend.tools.document_tool import DocumentTool
            self.document_tool = DocumentTool()
            self.register_tool("document", self.document_tool.execute)
            
            # Phase 2: Persona Mode (Removed)
            
            # Phase 2: MiroFish Tool
            from backend.tools.mirofish_tool import MiroFishTool
            self.mirofish_tool = MiroFishTool()
            self.register_tool("mirofish", self.mirofish_tool.execute)
            
            # Phase 2: Conditional Triggers (Removed)
            
            
            
            # COSMO Presentation — native slide generator
            from backend.tools.cosmo_tool import CosmoPresentationTool
            self.cosmo_tool = CosmoPresentationTool()
            self.tool_registry.register(
                "presentation", self.cosmo_tool.execute
            )
            logger.info("COSMO Presentation tool registered as native tool")
            
            # Add missing plan and expose tools
            from backend.tools.plan_tool import PlanTool
            from backend.tools.expose_tool import ExposeTool
            from backend.agent.planner import PlanManager
            
            self.plan_manager = PlanManager(session_id=self.session_id or "default")
            self.plan_tool = PlanTool(plan_manager=self.plan_manager)
            self.register_tool("plan", self.plan_tool.execute)
            
            self.expose_tool = ExposeTool(sandbox_manager.executor)
            self.register_tool("expose", self.expose_tool.execute)
            
            # MCP: Agentic connection tool
            from backend.tools.mcp_tool import MCPTool
            self.mcp_tool = MCPTool(self.mcp_client, sync_callback=self.sync_mcp_tools)
            self.register_tool("mcp_connect", self.mcp_tool.execute)
            
            # TODO: Add other tools later

            # Core Tool Registration
            self.file_tool = FileTool(sandbox_manager.filesystem)
            self.register_tool("file", self.file_tool.execute)

            self.search_tool = SearchTool()
            self.register_tool("search", self.search_tool.execute)

            from backend.tools.web_tool import WebTool
            self.web_tool = WebTool()
            self.register_tool("web_read", self.web_tool.execute)

            self.shell_tool = ShellTool(sandbox_manager.executor)
            self.register_tool("shell", self.shell_tool.execute)
            
            # Register dummy message handler to ensure history saving
            async def _dummy_message(**kwargs):
                return {"success": True, "output": "Message generated."}
            self.register_tool("message", _dummy_message)
            
            logger.info("CORE: Все расширенные инструменты успешно загружены")
        except Exception as e:
            logger.error(f"ERROR: Ошибка при инициализации инструментов: {e}")

    async def _init_mcp(self):
        """Initialize MCP connections and register discovered tools."""
        try:
            await self.mcp_client.connect_all()
            # Wait a few seconds for discovery to finish (MVP approach)
            await asyncio.sleep(5)
            
            mcp_tools = await self.mcp_client.discover_tools()
            for tool_def in mcp_tools:
                # Use a specific callback that routes to call_external_tool
                server_name = tool_def["function"]["_mcp_server"]
                tool_name = tool_def["function"]["_mcp_tool_name"]
                
                async def mcp_callback(s=server_name, t=tool_name, **params):
                    return await self.mcp_client.call_external_tool(s, t, params)
                
                self.tool_registry.register_mcp_tool(tool_def, mcp_callback)
            
            if mcp_tools:
                logger.info(f"CORE: Connected to MCP and registered {len(mcp_tools)} tools")
        except Exception as e:
            logger.error(f"ERROR: Failed to initialize MCP: {e}")

    async def sync_mcp_tools(self):
        """Re-scan MCP client for new tools and register them."""
        try:
            mcp_tools = await self.mcp_client.discover_tools()
            registered_count = 0
            for tool_def in mcp_tools:
                name = tool_def["function"]["name"]
                if name not in self.tool_registry.tools:
                    # Use a specific callback that routes to call_external_tool
                    server_name = tool_def["function"]["_mcp_server"]
                    tool_name = tool_def["function"]["_mcp_tool_name"]
                    
                    async def mcp_callback(s=server_name, t=tool_name, **params):
                        return await self.mcp_client.call_external_tool(s, t, params)
                    
                    self.tool_registry.register_mcp_tool(tool_def, mcp_callback)
                    registered_count += 1
            
            if registered_count > 0:
                logger.info(f"CORE: Synced MCP and registered {registered_count} NEW tools")
        except Exception as e:
            logger.error(f"ERROR: Failed to sync MCP tools: {e}")

    async def process_task(self, task_description: str, websocket_send: Callable = None, stream: bool = False, **kwargs) -> ExecutionResult:
        """Обработать задачу с использованием мультиагентной оркестрации."""
        task_id = str(uuid.uuid4())
        start_time = asyncio.get_running_loop().time()
        
        # Get execution mode (Fast vs Planning)
        mode_str = kwargs.get("mode", "planning").lower()
        mode = AgentMode.FAST if mode_str == "fast" else AgentMode.PLANNING
        
        try:
            logger.info(f"TASK: Начало мультиагентной обработки ({mode.value}): {task_description}")
            self.state = AgentState.PLANNING if mode == AgentMode.PLANNING else AgentState.EXECUTING
            
            if websocket_send:
                await websocket_send({
                    "type": "message_info", 
                    "content": f"🚀 Archimedes перешел в режим: **{mode.value.upper()}**\nЗапуск задачи: {task_description}"
                })
            
            # Delegate to Orchestrator
            orch_result = await self.orchestrator.run_task(
                task_description=task_description,
                mode=mode,
                session_id=self.session_id or "default",
                websocket_send=websocket_send,
                task_hint=kwargs.get("task_hint", "default"),
                stream=stream
            )
            
            if not orch_result.get("success"):
                raise Exception(orch_result.get("error", "Orchestrator failed without error message"))
            
            # Send final result to user
            final_output = orch_result.get("output", "Задача выполнена.")
            if websocket_send and final_output:
                await websocket_send({"type": "message_result", "content": str(final_output)})
            
            self.state = AgentState.COMPLETED
            result = ExecutionResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                output=final_output,
                duration=asyncio.get_running_loop().time() - start_time,
                metadata={
                    "mode": mode.value,
                    "plan": orch_result.get("plan")
                }
            )
            
            self.results[task_id] = result
            self.execution_history.append(result)
            
            logger.info(f"DONE: Задача завершена за {result.duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"ERROR: Ошибка при обработке задачи: {str(e)}")
            if websocket_send:
                await websocket_send({"type": "agent_error", "content": f"Критическая ошибка оркестрации: {str(e)}"})
            
            # Orchestrator errors are bubbled up here.
            # Internal retries are handled by Orchestrator's ExecutorAgent.
            # If we reach here, it's a fatal task failure.
            
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

    async def _create_plan(self, task_id: str, description: str, websocket_send: Callable = None, **kwargs) -> TaskPlan:
        """Создать интеллектуальный план выполнения."""
        if websocket_send:
            await websocket_send({"type": "thought", "content": f"Разрабатываю стратегию выполнения задачи: '{description}'"})
        
        # Добавляем новую задачу в существующую историю (сохраняем контекст)
        # Если история пуста — инициализируем системным промтом
        if not self.history or self.history[0].get("role") != "system":
            self.history = [{"role": "system", "content": self.system_prompt}]
        self.history.append({"role": "user", "content": description})
        
        # Добавить новое сообщение в context_manager (без полного сброса)
        self.context_manager.add_message("user", description)
        
        # Проверить нужна ли summarization контекста
        try:
            await self.context_manager.summarize_if_needed(self.router)
            self.history = self.context_manager.get_messages()
        except Exception as e:
            logger.warning(f"Context summarization skipped: {e}")
        
        # Анализ задачи
        complexity = self._analyze_complexity(description)
        
        # Определение стратегии
        strategy = "adaptive" if complexity > 0.7 else "sequential"
        
        # Разбиение на подзадачи
        subtasks = await self._decompose_task(description, complexity)
        
        plan = TaskPlan(
            task_id=task_id,
            description=description,
            subtasks=subtasks,
            strategy=strategy,
            priority=kwargs.get("priority", 1),
            estimated_duration=complexity * 10  # Примерная оценка
        )
        
        return plan

    async def _execute_plan(self, task_id: str, plan: TaskPlan, websocket_send: Callable = None) -> Any:
        """Выполнить план с оптимальной стратегией."""
        results = []
        
        if plan.strategy == "parallel":
            # Параллельное выполнение
            tasks = [
                self._execute_subtask(task_id, subtask, websocket_send=websocket_send)
                for subtask in plan.subtasks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Последовательное выполнение
            for subtask in plan.subtasks:
                result = await self._execute_subtask(task_id, subtask, websocket_send=websocket_send)
                results.append(result)
        
        return self._synthesize_results(results)

    async def _execute_subtask(self, task_id: str, subtask: Dict[str, Any], websocket_send: Callable = None) -> Any:
        """Выполнить подзадачу с использованием LLM и инструментов."""
        try:
            subtask_type = subtask.get("type", "generic")
            
            # Simple notification about action
            action_map = {
                "analyze": "Провожу детальный анализ задачи...",
                "execute": "Приступаю к выполнению основного этапа...",
                "verify": "Проверяю результаты выполнения...",
                "optimize": "Оптимизирую решение и чищу временные файлы...",
                "plan": "Уточняю план действий..."
            }
            
            msg = action_map.get(subtask_type, f"Выполняю этап: {subtask_type}")
            if websocket_send:
                await websocket_send({"type": "message_info", "content": msg})

            # For core logic steps, we use the LLM loop
            if subtask_type in ["execute", "analyze", "verify", "optimize"]:
                # Real intelligent execution loop
                max_steps = settings.AGENT_MAX_ITERATIONS
                subtask_results = []
                
                for step in range(max_steps):
                    async def handle_token(token_event):
                        if websocket_send:
                            await websocket_send(token_event)

                    # Request model for next action
                    if hasattr(self.router, "generate_stream"):
                        response = await self.router.generate_stream(
                            messages=self.history,
                            tools=self._get_tool_definitions(),
                            task_hint="think" if step == 0 else "default",
                            on_token=handle_token
                        )
                    else:
                        response = await self.router.generate(
                            messages=self.history,
                            tools=self._get_tool_definitions(),
                            task_hint="think" if step == 0 else "default"
                        )
                    
                    thought = response.get("thought", "")
                    if thought and websocket_send:
                        await websocket_send({"type": "thought", "content": thought})
                    
                    tool_call = response.get("tool_call")
                    if tool_call:
                        t_name = tool_call["name"]
                        t_params = tool_call["params"]
                        
                        if websocket_send:
                            # User friendly tool notification instead of JSON
                            shell_str = f"Запускаю команду в терминале...\n$ {t_params.get('command', '')}" if t_name == "shell" else "Запускаю команду в терминале..."
                            
                            file_str = f"Работаю с файлом {t_params.get('path', '')}..."
                            if t_name == "file" and t_params.get("action") == "write":
                                ext = str(t_params.get("path", "")).split(".")[-1]
                                content_preview = str(t_params.get("content", ""))
                                file_str = f"Создан/Изменен файл: {t_params.get('path', '')}\n```{ext}\n{content_preview}\n```"

                            friendly_names = {
                                "search": f"Ищу информацию: {t_params.get('query', '')}...",
                                "file": file_str,
                                "shell": shell_str,
                                "browser": "Изучаю веб-страницу..."
                            }
                            await websocket_send({
                                "type": "message_info", 
                                "content": friendly_names.get(t_name, f"Использую инструмент: {t_name}")
                            })

                        # Execute registered tool
                        if t_name in self.tools:
                            # Standardize tool call for history
                            call_id = f"call_{str(uuid.uuid4())[:8]}"
                            std_tool_call = {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": t_name,
                                    "arguments": t_params  # Store as dict, clients will handle stringification if needed
                                }
                            }

                            TOOLS_NEEDING_SESSION = ["file", "shell", "browser", "voice", "document", "slides", "expose", "plan", "monitor"]
                            t_args = {**t_params}
                            if t_name in TOOLS_NEEDING_SESSION:
                                t_args["session_id"] = self.session_id
                            
                            res = await self.tools[t_name](**t_args)
                            
                            # Extract output for model and logs
                            if res.get("success") is False:
                                tool_output = f"ERROR: {res.get('error', 'Unknown error')}"
                            else:
                                tool_output = str(res.get("output", res.get("content", "OK")))
                                
                            logger.info(f"TOOL EXECUTION FINISHED: {t_name}. Result length: {len(tool_output)}")
                            
                            # Log to history in STANDARD format using ContextManager
                            self.context_manager.add_message("assistant", thought or "", tool_calls=[std_tool_call])
                            self.context_manager.add_message("tool", tool_output, tool_call_id=call_id, name=t_name)
                            
                            # Проверить нужна ли summarization
                            await self.context_manager.summarize_if_needed(self.router)
                            
                            # Синхронизировать self.history с context_manager
                            self.history = self.context_manager.get_messages()
                            
                            # Artifact support
                            if t_name == "file" and t_params.get("action") == "write" and res.get("success"):
                                if websocket_send:
                                    await websocket_send({
                                        "type": "artifact", 
                                        "name": os.path.basename(t_params.get("path", "file")),
                                        "content": t_params.get("content", ""),
                                        "language": "markdown" if t_params.get("path", "").endswith(".md") else "plaintext"
                                    })
                        
                            # --- AUTO-VERIFICATION (Placeholder) ---

                            # --- AUTO-VERIFICATION ---
                            original_task = ""
                            for msg in self.history:
                                if msg.get("role") == "user":
                                    original_task = msg.get("content", "")
                                    break

                            verification_prompt = f"""
The original task was: {original_task}
The proposed result is: {t_params.get('content')}
Did the agent completely solve the task?
If yes, reply ONLY with 'VERIFIED'.
If no, explain what is missing in 1-2 sentences.
"""
                            verdict_resp = await self.router.generate(
                                messages=[{"role": "user", "content": verification_prompt}],
                                task_hint="think"
                            )
                            verdict = verdict_resp.get("text", "")
                            
                            if "VERIFIED" not in verdict.upper() and step < max_steps - 2:
                                self.context_manager.add_message("system", f"Subtask not fully completed. Missing: {verdict}. Continue working.")
                                self.history = self.context_manager.get_messages()
                                continue  # Возврат в цикл LLM
                            # -------------------------
                            
                            subtask_results.append({
                                "step": step,
                                "action": "complete",
                                "result": t_params.get("content")
                            })
                            return {"status": "completed", "result": t_params.get("content"), "steps": subtask_results}
                    else:
                        # No more tool calls, subtask finished
                        return response.get("text", "Готово")
                
                return "Достигнут лимит шагов подзадачи"

            # Fallback for simple registered tools
            if subtask_type in self.tools:
                tool = self.tools[subtask_type]
                await asyncio.sleep(1)
                
                tool_args = {**subtask.get("params", {})}
                if subtask_type in ["file", "shell", "browser"]:
                     tool_args["session_id"] = self.session_id
                
                return await tool(**tool_args)
            
            return {"status": "success", "step": subtask_type}
                
        except Exception as e:
            logger.error(f"ERROR: Ошибка в подзадаче: {str(e)}")
            raise

    async def _handle_error_with_recovery(self, task_id: str, error: str, 
                                         original_task: str) -> ExecutionResult:
        """Обработать ошибку с попыткой восстановления."""
        logger.info("RECOVERY: Попытка восстановления после ошибки...")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"RECOVERY: Попытка {attempt + 1}/{self.max_retries}")
                
                # Создать альтернативный план
                alt_plan = await self._create_alternative_plan(original_task)
                output = await self._execute_plan(task_id, alt_plan)
                
                return ExecutionResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    metadata={"recovery_attempt": attempt + 1}
                )
                
            except Exception as e:
                logger.warning(f"WARN: Попытка {attempt + 1} не удалась: {str(e)}")
                continue
        
        return ExecutionResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=f"Не удалось восстановиться после ошибки: {error}"
        )

    async def _create_alternative_plan(self, task_description: str) -> TaskPlan:
        """Создать альтернативный план при ошибке."""
        task_id = str(uuid.uuid4())
        
        # Упрощенный план с меньшей сложностью
        subtasks = [
            {
                "type": "analyze",
                "params": {"task": task_description}
            },
            {
                "type": "execute_simple",
                "params": {"task": task_description}
            }
        ]
        
        return TaskPlan(
            task_id=task_id,
            description=task_description,
            subtasks=subtasks,
            strategy="sequential"
        )

    def register_tool(self, name: str, handler: Callable) -> None:
        """Зарегистрировать инструмент."""
        # Backward compatibility for direct dict
        self.tools[name] = handler
        # New: Register in the tool_registry for agents
        self.tool_registry.register(name, handler)
        logger.info(f"TOOL: Инструмент зарегистрирован: {name}")

    def register_error_handler(self, error_type: str, handler: Callable) -> None:
        """Зарегистрировать обработчик ошибок."""
        self.error_handlers[error_type] = handler
        logger.info(f"HANDLER: Обработчик ошибок зарегистрирован: {error_type}")

    def _analyze_complexity(self, task_description: str) -> float:
        """Анализировать сложность задачи (0.0 - 1.0)."""
        keywords_complex = ["анализ", "исследование", "оптимизация", "интеграция"]
        keywords_simple = ["создать", "удалить", "скопировать"]
        
        desc_lower = task_description.lower()
        
        complexity_score = 0.5  # Базовое значение
        
        for keyword in keywords_complex:
            if keyword in desc_lower:
                complexity_score += 0.2
        
        for keyword in keywords_simple:
            if keyword in desc_lower:
                complexity_score -= 0.1
        
        return min(1.0, max(0.0, complexity_score))

    async def _decompose_task(self, description: str, complexity: float) -> List[Dict[str, Any]]:
        """Разложить задачу на подзадачи."""
        subtasks = []
        
        if complexity > 0.7:
            # Сложная задача - больше подзадач
            subtasks = [
                {"type": "analyze", "params": {"task": description}},
                {"type": "plan", "params": {"task": description}},
                {"type": "execute", "params": {"task": description}},
                {"type": "verify", "params": {"task": description}},
                {"type": "optimize", "params": {"task": description}}
            ]
        elif complexity > 0.4:
            # Средняя задача
            subtasks = [
                {"type": "analyze", "params": {"task": description}},
                {"type": "execute", "params": {"task": description}},
                {"type": "verify", "params": {"task": description}}
            ]
        else:
            # Простая задача
            subtasks = [
                {"type": "execute", "params": {"task": description}}
            ]
        
        return subtasks

    def _synthesize_results(self, results: List[Any]) -> Dict[str, Any]:
        """Синтезировать результаты подзадач."""
        return {
            "total_subtasks": len(results),
            "successful": sum(1 for r in results if not isinstance(r, Exception)),
            "failed": sum(1 for r in results if isinstance(r, Exception)),
            "results": results
        }

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Получить определения всех инструментов для LLM."""
        definitions = []
        try:
            # Собираем из всех инстансов с get_definition()
            for attr_name in dir(self):
                obj = getattr(self, attr_name, None)
                if obj and hasattr(obj, 'get_definition') and callable(obj.get_definition):
                    try:
                        defn = obj.get_definition()
                        if "function" in defn:
                            definitions.append(defn)
                    except Exception:
                        pass
            
            # Добавляем message tool вручную
            definitions.append({
                "type": "function",
                "function": {
                    "name": "message",
                    "description": "Send a final result to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["result"]},
                            "content": {"type": "string"}
                        },
                        "required": ["type", "content"]
                    }
                }
            })
        except Exception as e:
            logger.warning(f"FAILED TO GET TOOL DEFS: {e}")
            
        logger.info(f"RETURNING {len(definitions)} TOOL DEFINITIONS TO LLM: {[d.get('function', {}).get('name', 'unknown') for d in definitions]}")
        return definitions

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику работы агента."""
        completed = sum(1 for r in self.execution_history if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in self.execution_history if r.status == TaskStatus.FAILED)
        total_duration = sum(r.duration for r in self.execution_history)
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "total_tasks": len(self.execution_history),
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / len(self.execution_history) * 100) if self.execution_history else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / len(self.execution_history) if self.execution_history else 0,
            "registered_tools": len(self.tools)
        }

    async def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус агента."""
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
