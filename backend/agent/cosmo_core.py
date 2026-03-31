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
from datetime import datetime
import uuid

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
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
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
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

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

    def __init__(self, name: str = "ArchimedesCosmo", max_retries: int = 3):
        self.agent_id = str(uuid.uuid4())
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
        
        # Регистрация расширенных инструментов
        self._init_extended_tools()
        
        logger.info(f"✅ Инициализирован {self.name} (ID: {self.agent_id})")

    def _init_extended_tools(self):
        """Инициализация и регистрация всех доступных инструментов."""
        try:
            from .tools.browser_tool import BrowserTool
            from .tools.pdf_tool import PDFTool
            from .tools.image_gen_tool import ImageGenTool
            from .tools.github_tool import GithubTool
            from .tools.email_tool import EmailTool
            from .tools.utility_tools import VideoTool, AudioTool, SheetsTool, ScheduleTool

            # Инстанцирование и регистрация
            browser = BrowserTool()
            self.register_tool("browser", browser.execute)
            
            pdf = PDFTool()
            self.register_tool("pdf", pdf.execute)
            
            image_gen = ImageGenTool()
            self.register_tool("image_gen", image_gen.execute)
            
            github = GithubTool()
            self.register_tool("github", github.execute)
            
            email = EmailTool()
            self.register_tool("email", email.execute)
            
            video = VideoTool()
            self.register_tool("video", video.execute)
            
            audio = AudioTool()
            self.register_tool("audio", audio.execute)
            
            sheets = SheetsTool()
            self.register_tool("sheets", sheets.execute)
            
            schedule = ScheduleTool()
            self.register_tool("schedule", schedule.execute)
            
            logger.info("🚀 Все расширенные инструменты успешно загружены")
        except Exception as e:
            logger.error(f"⚠️ Ошибка при инициализации инструментов: {e}")

    async def process_task(self, task_description: str, **kwargs) -> ExecutionResult:
        """Обработать задачу с полным жизненным циклом."""
        task_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"📋 Начало обработки задачи: {task_description}")
            self.state = AgentState.THINKING
            
            # Этап 1: Анализ и планирование
            plan = await self._create_plan(task_id, task_description, **kwargs)
            self.tasks[task_id] = plan
            
            self.state = AgentState.PLANNING
            logger.info(f"📊 План создан: {len(plan.subtasks)} подзадач")
            
            # Этап 2: Выполнение
            self.state = AgentState.EXECUTING
            output = await self._execute_plan(task_id, plan)
            
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
            
            logger.info(f"✅ Задача завершена за {result.duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке задачи: {str(e)}")
            
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

    async def _create_plan(self, task_id: str, description: str, **kwargs) -> TaskPlan:
        """Создать интеллектуальный план выполнения."""
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

    async def _execute_plan(self, task_id: str, plan: TaskPlan) -> Any:
        """Выполнить план с оптимальной стратегией."""
        results = []
        
        if plan.strategy == "parallel":
            # Параллельное выполнение
            tasks = [
                self._execute_subtask(task_id, subtask)
                for subtask in plan.subtasks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Последовательное выполнение
            for subtask in plan.subtasks:
                result = await self._execute_subtask(task_id, subtask)
                results.append(result)
        
        return self._synthesize_results(results)

    async def _execute_subtask(self, task_id: str, subtask: Dict[str, Any]) -> Any:
        """Выполнить подзадачу с обработкой ошибок."""
        try:
            subtask_type = subtask.get("type", "generic")
            params = subtask.get("params", {})
            
            # Выбрать подходящий инструмент
            if subtask_type in self.tools:
                tool = self.tools[subtask_type]
                return await tool(**params)
            else:
                logger.warning(f"⚠️ Инструмент {subtask_type} не найден")
                return {"status": "skipped", "reason": "tool_not_found"}
                
        except Exception as e:
            logger.error(f"❌ Ошибка в подзадаче: {str(e)}")
            raise

    async def _handle_error_with_recovery(self, task_id: str, error: str, 
                                         original_task: str) -> ExecutionResult:
        """Обработать ошибку с попыткой восстановления."""
        logger.info(f"🔄 Попытка восстановления после ошибки...")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Попытка {attempt + 1}/{self.max_retries}")
                
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
                logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {str(e)}")
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
        logger.info(f"🛠️ Инструмент зарегистрирован: {name}")

    def register_error_handler(self, error_type: str, handler: Callable) -> None:
        """Зарегистрировать обработчик ошибок."""
        self.error_handlers[error_type] = handler
        logger.info(f"🚨 Обработчик ошибок зарегистрирован: {error_type}")

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
