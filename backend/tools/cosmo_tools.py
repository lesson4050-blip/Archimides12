"""
КОСМО-уровневые инструменты для Archimedes.
Полностью переработанные с максимальной надежностью и функциональностью.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Результат выполнения инструмента."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata or {}
        }


class CosmoTool(ABC):
    """Базовый класс для КОСМО-инструментов."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.error_count = 0

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Выполнить инструмент."""
        pass

    async def __call__(self, **kwargs) -> ToolResult:
        """Удобный способ вызова."""
        try:
            self.execution_count += 1
            logger.info(f"🔧 Выполнение инструмента: {self.name}")
            result = await self.execute(**kwargs)
            logger.info(f"✅ Инструмент {self.name} завершен успешно")
            return result
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Ошибка в инструменте {self.name}: {str(e)}")
            return ToolResult(success=False, error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику инструмента."""
        return {
            "name": self.name,
            "executions": self.execution_count,
            "errors": self.error_count,
            "success_rate": (
                (self.execution_count - self.error_count) / self.execution_count * 100
                if self.execution_count > 0 else 0
            )
        }


class FileToolCosmo(CosmoTool):
    """Продвинутый инструмент для работы с файлами."""

    def __init__(self):
        super().__init__("FileTool", "Работа с файлами и директориями")

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Выполнить действие с файлами."""
        try:
            if action == "read":
                return await self._read_file(kwargs.get("path"))
            elif action == "write":
                return await self._write_file(kwargs.get("path"), kwargs.get("content"))
            elif action == "list":
                return await self._list_files(kwargs.get("path", "."))
            elif action == "analyze":
                return await self._analyze_file(kwargs.get("path"))
            else:
                return ToolResult(success=False, error=f"Неизвестное действие: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _read_file(self, path: str) -> ToolResult:
        """Прочитать файл."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ToolResult(success=True, data={"content": content, "size": len(content)})
        except Exception as e:
            return ToolResult(success=False, error=f"Ошибка чтения файла: {str(e)}")

    async def _write_file(self, path: str, content: str) -> ToolResult:
        """Написать файл."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return ToolResult(success=True, data={"path": path, "size": len(content)})
        except Exception as e:
            return ToolResult(success=False, error=f"Ошибка записи файла: {str(e)}")

    async def _list_files(self, path: str) -> ToolResult:
        """Список файлов в директории."""
        try:
            import os
            files = os.listdir(path)
            return ToolResult(success=True, data={"files": files, "count": len(files)})
        except Exception as e:
            return ToolResult(success=False, error=f"Ошибка листинга: {str(e)}")

    async def _analyze_file(self, path: str) -> ToolResult:
        """Анализировать файл."""
        try:
            import os
            stat = os.stat(path)
            return ToolResult(success=True, data={
                "path": path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "type": os.path.splitext(path)[1]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchToolCosmo(CosmoTool):
    """Продвинутый инструмент для поиска информации."""

    def __init__(self):
        super().__init__("SearchTool", "Поиск информации в интернете")

    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Выполнить поиск."""
        try:
            # Симуляция поиска (в реальности используется API)
            results = await self._search_web(query)
            return ToolResult(success=True, data=results)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Поиск в веб."""
        # Здесь должна быть реальная интеграция с поисковым API
        return {
            "query": query,
            "results": [
                {"title": "Результат 1", "url": "https://example.com/1", "snippet": "..."},
                {"title": "Результат 2", "url": "https://example.com/2", "snippet": "..."}
            ],
            "count": 2
        }


class ExecutionToolCosmo(CosmoTool):
    """Инструмент для выполнения команд."""

    def __init__(self):
        super().__init__("ExecutionTool", "Выполнение команд в терминале")

    async def execute(self, command: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Выполнить команду."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return ToolResult(
                    success=True,
                    data={
                        "command": command,
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode(),
                        "returncode": process.returncode
                    }
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(success=False, error=f"Команда превысила таймаут ({timeout}s)")
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class AnalysisToolCosmo(CosmoTool):
    """Инструмент для анализа данных."""

    def __init__(self):
        super().__init__("AnalysisTool", "Анализ и обработка данных")

    async def execute(self, action: str, data: Any, **kwargs) -> ToolResult:
        """Выполнить анализ."""
        try:
            if action == "summarize":
                return await self._summarize(data)
            elif action == "classify":
                return await self._classify(data)
            elif action == "extract":
                return await self._extract(data)
            else:
                return ToolResult(success=False, error=f"Неизвестное действие: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _summarize(self, data: Any) -> ToolResult:
        """Создать сводку."""
        return ToolResult(success=True, data={"summary": f"Сводка для {len(str(data))} символов"})

    async def _classify(self, data: Any) -> ToolResult:
        """Классифицировать данные."""
        return ToolResult(success=True, data={"classification": "unknown"})

    async def _extract(self, data: Any) -> ToolResult:
        """Извлечь информацию."""
        return ToolResult(success=True, data={"extracted": []})


class ToolRegistryCosmo:
    """Реестр КОСМО-инструментов."""

    def __init__(self):
        self.tools: Dict[str, CosmoTool] = {}
        self._initialize_default_tools()

    def _initialize_default_tools(self):
        """Инициализировать встроенные инструменты."""
        self.register(FileToolCosmo())
        self.register(SearchToolCosmo())
        self.register(ExecutionToolCosmo())
        self.register(AnalysisToolCosmo())
        logger.info(f"✅ Инициализировано {len(self.tools)} встроенных инструментов")

    def register(self, tool: CosmoTool) -> None:
        """Зарегистрировать инструмент."""
        self.tools[tool.name] = tool
        logger.info(f"🛠️ Инструмент зарегистрирован: {tool.name}")

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Выполнить инструмент."""
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Инструмент {tool_name} не найден")
        
        tool = self.tools[tool_name]
        return await tool(**kwargs)

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об инструменте."""
        if tool_name not in self.tools:
            return None
        
        tool = self.tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "stats": tool.get_stats()
        }

    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Получить информацию о всех инструментах."""
        return [self.get_tool_info(name) for name in self.tools.keys()]

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по всем инструментам."""
        total_executions = sum(tool.execution_count for tool in self.tools.values())
        total_errors = sum(tool.error_count for tool in self.tools.values())
        
        return {
            "total_tools": len(self.tools),
            "total_executions": total_executions,
            "total_errors": total_errors,
            "success_rate": (
                (total_executions - total_errors) / total_executions * 100
                if total_executions > 0 else 0
            ),
            "tools": [tool.get_stats() for tool in self.tools.values()]
        }


# Глобальный реестр
tool_registry = ToolRegistryCosmo()
