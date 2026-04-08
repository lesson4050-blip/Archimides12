"""
КОСМО-уровневое ядро агента Archimedes.
Полностью переработанная архитектура с максимальной надежностью и производительностью.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import datetime
import os
import uuid

from backend.models.model_router import ModelRouter
from backend.agent.thought_engine import ThoughtEngine

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
        
        # Регистрация расширенных инструментов
        self._init_extended_tools()
        
        logger.info(f"OK: Инициализирован {self.name} (ID: {self.agent_id})")

    def _init_extended_tools(self):
        """Инициализация и регистрация всех доступных инструментов."""
        try:
            from .tools.pdf_tool import PDFTool
            from .tools.image_gen_tool import ImageGenTool
            from .tools.github_tool import GithubTool
            from .tools.email_tool import EmailTool
            from .tools.utility_tools import VideoTool, AudioTool, SheetsTool, ScheduleTool
            
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

            # Core Tool Registration
            self.file_tool = FileTool(sandbox_manager.filesystem)
            self.register_tool("file", self.file_tool.execute)

            self.search_tool = SearchTool()
            self.register_tool("search", self.search_tool.execute)

            self.shell_tool = ShellTool(sandbox_manager.executor)
            self.register_tool("shell", self.shell_tool.execute)
            
            logger.info("CORE: Все расширенные инструменты успешно загружены")
        except Exception as e:
            logger.error(f"ERROR: Ошибка при инициализации инструментов: {e}")

    async def process_task(self, task_description: str, websocket_send: Callable = None, **kwargs) -> ExecutionResult:
        """Обработать задачу с полным жизненным циклом."""
        task_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"TASK: Начало обработки задачи: {task_description}")
            self.state = AgentState.THINKING
            
            if websocket_send:
                await websocket_send({"type": "message_info", "content": f"TASK: Принята новая задача:\n\n{task_description}"})
            
            # Этап 1: Анализ и планирование
            plan = await self._create_plan(task_id, task_description, websocket_send=websocket_send, **kwargs)
            self.tasks[task_id] = plan
            
            self.state = AgentState.PLANNING
            logger.info(f"PLAN: План создан: {len(plan.subtasks)} подзадач")
            if websocket_send:
                await websocket_send({"type": "message_info", "content": f"PLAN: Создан план выполнения из {len(plan.subtasks)} этапов (Стратегия: {plan.strategy})."})
            
            # Этап 2: Выполнение
            self.state = AgentState.EXECUTING
            output = await self._execute_plan(task_id, plan, websocket_send=websocket_send)
            
            # Этап 3: Синтез результата
            result = ExecutionResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                output=output,
                duration=asyncio.get_event_loop().time() - start_time,
                metadata={
                    "subtasks": len(plan.subtasks),
                    "strategy": plan.strategy
                }
            )
            
            self.state = AgentState.COMPLETED
            self.results[task_id] = result
            self.execution_history.append(result)
            
            logger.info(f"DONE: Задача завершена за {result.duration:.2f}s")
            if websocket_send:
                formatted_output = str(output) if output else "Успешно"
                await websocket_send({"type": "message_result", "content": f"DONE: Задача завершена за {result.duration:.2f}s.\n\nРезультат: {formatted_output}"})
            return result
            
        except Exception as e:
            logger.error(f"ERROR: Ошибка при обработке задачи: {str(e)}")
            if websocket_send:
                await websocket_send({"type": "agent_error", "content": f"ERROR: Возникла ошибка: {str(e)}"})
            
            # Попытка восстановления
            if self.max_retries > 0:
                self.state = AgentState.RECOVERING
                return await self._handle_error_with_recovery(task_id, str(e), task_description)
            
            result = ExecutionResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                duration=asyncio.get_event_loop().time() - start_time
            )
            
            self.state = AgentState.ERROR
            self.results[task_id] = result
            self.execution_history.append(result)
            return result

    async def _create_plan(self, task_id: str, description: str, websocket_send: Callable = None, **kwargs) -> TaskPlan:
        """Создать интеллектуальный план выполнения."""
        if websocket_send:
            await websocket_send({"type": "thought", "content": f"Разрабатываю стратегию выполнения задачи: '{description}'"})
        
        # Добавляем задачу в историю как отправную точку
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.history.append({"role": "user", "content": description})
        
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
            task_desc = subtask.get("params", {}).get("task", "")
            
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
                max_steps = 5
                subtask_results = []
                
                for step in range(max_steps):
                    # Request model for next action
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
                            friendly_names = {
                                "search": "Ищу информацию в интернете...",
                                "file": f"Работаю с файлом {t_params.get('path', '')}...",
                                "shell": "Запускаю команду в терминале...",
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

                            t_args = {**t_params}
                            if t_name in ["file", "shell", "browser"]:
                                t_args["session_id"] = self.session_id
                            
                            res = await self.tools[t_name](**t_args)
                            
                            # Log to history in STANDARD format
                            self.history.append({
                                "role": "assistant", 
                                "content": thought, 
                                "tool_calls": [std_tool_call]
                            })
                            self.history.append({
                                "role": "tool", 
                                "tool_call_id": call_id, 
                                "name": t_name, 
                                "content": str(res.get("output", res.get("content", "OK")))
                            })
                            
                            # Artifact support
                            if t_name == "file" and t_params.get("action") == "write" and res.get("success"):
                                if websocket_send:
                                    await websocket_send({
                                        "type": "artifact", 
                                        "name": os.path.basename(t_params.get("path", "file")),
                                        "content": t_params.get("content", ""),
                                        "language": "markdown" if t_params.get("path", "").endswith(".md") else "plaintext"
                                    })
                        
                        if t_name == "message" and t_params.get("type") == "result":
                            return t_params.get("content")
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
        logger.info(f"RECOVERY: Попытка восстановления после ошибки...")
        
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
        self.tools[name] = handler
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
            # Используем уже инициализированные экземпляры инструментов
            tool_instances = [
                self.file_tool, 
                self.search_tool, 
                self.shell_tool, 
                self.browser_tool,
                self.pdf_tool,
                self.image_gen_tool,
                self.github_tool,
                self.email_tool
            ]
            
            for tool in tool_instances:
                if hasattr(tool, "get_definition"):
                    defn = tool.get_definition()
                    # Ensure it's wrapped in standard OpenAI format
                    if "function" not in defn:
                        wrapped = {
                            "type": "function",
                            "function": {
                                "name": defn["name"],
                                "description": defn["description"],
                                "parameters": defn["parameters"]
                            }
                        }
                        definitions.append(wrapped)
                    else:
                        definitions.append(defn)
            
            # Дополнительный инструмент для завершения задачи
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
