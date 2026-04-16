"""
КОСМО-уровневые API маршруты для Archimedes.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from backend.auth.dependencies import get_current_user, require_admin
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["cosmo"])


# Модели
class TaskRequest(BaseModel):
    """Запрос на выполнение задачи."""
    description: str
    priority: int = 1
    timeout: int = 300


class TaskResponse(BaseModel):
    """Ответ о задаче."""
    task_id: str
    status: str
    created_at: str
    data: Optional[Dict[str, Any]] = None


class AgentStatus(BaseModel):
    """Статус агента."""
    agent_id: str
    state: str
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime: float


# Хранилище (в реальности - БД)
tasks_storage: Dict[str, Dict[str, Any]] = {}
agent_data: Dict[str, Any] = {
    "agent_id": str(uuid.uuid4()),
    "state": "idle",
    "active_tasks": 0,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "start_time": datetime.now()
}


# Endpoints
@router.get("/health", summary="Проверка здоровья сервера")
async def health_check() -> Dict[str, Any]:
    """Проверить здоровье сервера."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-cosmo"
    }


@router.get("/agent/status", summary="Получить статус агента", response_model=AgentStatus)
async def get_agent_status(user: dict = Depends(get_current_user)) -> AgentStatus:
    """Получить текущий статус агента."""
    uptime = (datetime.now() - agent_data["start_time"]).total_seconds()
    
    return AgentStatus(
        agent_id=agent_data["agent_id"],
        state=agent_data["state"],
        active_tasks=agent_data["active_tasks"],
        completed_tasks=agent_data["completed_tasks"],
        failed_tasks=agent_data["failed_tasks"],
        uptime=uptime
    )


@router.post("/tasks", summary="Создать новую задачу", response_model=TaskResponse)
async def create_task(request: TaskRequest, user: dict = Depends(get_current_user)) -> TaskResponse:
    """Создать новую задачу для выполнения."""
    task_id = str(uuid.uuid4())
    
    task = {
        "task_id": task_id,
        "description": request.description,
        "priority": request.priority,
        "timeout": request.timeout,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None
    }
    
    tasks_storage[task_id] = task
    agent_data["active_tasks"] += 1
    
    logger.info(f"📋 Создана задача: {task_id}")
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=task["created_at"]
    )


@router.get("/tasks/{task_id}", summary="Получить информацию о задаче")
async def get_task(task_id: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Получить информацию о конкретной задаче."""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return tasks_storage[task_id]


@router.get("/tasks", summary="Получить список всех задач")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Получить список всех задач."""
    tasks = list(tasks_storage.values())
    
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    
    total = len(tasks)
    tasks = tasks[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "tasks": tasks
    }


@router.put("/tasks/{task_id}", summary="Обновить задачу")
async def update_task(task_id: str, update: Dict[str, Any], user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Обновить информацию о задаче."""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    
    # Обновить поля
    if "status" in update:
        old_status = task["status"]
        task["status"] = update["status"]
        
        # Обновить счетчики агента
        if old_status == "pending" and update["status"] == "completed":
            agent_data["active_tasks"] -= 1
            agent_data["completed_tasks"] += 1
        elif old_status == "pending" and update["status"] == "failed":
            agent_data["active_tasks"] -= 1
            agent_data["failed_tasks"] += 1
    
    if "result" in update:
        task["result"] = update["result"]
    
    task["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"✏️ Обновлена задача: {task_id}")
    
    return task


@router.delete("/tasks/{task_id}", summary="Удалить задачу")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Удалить задачу."""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage.pop(task_id)
    
    if task["status"] == "pending":
        agent_data["active_tasks"] -= 1
    
    logger.info(f"🗑️ Удалена задача: {task_id}")
    
    return {"message": "Задача удалена", "task_id": task_id}


@router.get("/statistics", summary="Получить статистику")
async def get_statistics(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Получить статистику работы агента."""
    uptime = (datetime.now() - agent_data["start_time"]).total_seconds()
    total_tasks = agent_data["completed_tasks"] + agent_data["failed_tasks"]
    success_rate = (
        (agent_data["completed_tasks"] / total_tasks * 100)
        if total_tasks > 0 else 0
    )
    
    return {
        "agent_id": agent_data["agent_id"],
        "uptime_seconds": uptime,
        "total_tasks": total_tasks,
        "completed_tasks": agent_data["completed_tasks"],
        "failed_tasks": agent_data["failed_tasks"],
        "active_tasks": agent_data["active_tasks"],
        "success_rate": success_rate,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/execute", summary="Выполнить команду")
async def execute_command(command: Dict[str, str], user: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Выполнить команду на агенте."""
    cmd = command.get("command", "")
    
    if not cmd:
        raise HTTPException(status_code=400, detail="Команда не предоставлена")
    
    # Создать задачу для выполнения
    task_id = str(uuid.uuid4())
    
    return {
        "task_id": task_id,
        "command": cmd,
        "status": "queued",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/info", summary="Получить информацию об агенте")
async def get_agent_info() -> Dict[str, Any]:
    """Получить информацию об агенте."""
    return {
        "name": "Archimedes COSMO",
        "version": "2.0.0",
        "description": "КОСМО-уровневый автономный ИИ-агент",
        "capabilities": [
            "Планирование и выполнение задач",
            "Работа с файлами",
            "Веб-поиск и анализ",
            "Выполнение команд",
            "Управление памятью",
            "Восстановление ошибок"
        ],
        "api_version": "1.0",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/reset", summary="Сбросить агента")
async def reset_agent(user: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Сбросить состояние агента."""
    global tasks_storage, agent_data
    
    tasks_storage = {}
    agent_data = {
        "agent_id": str(uuid.uuid4()),
        "state": "idle",
        "active_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "start_time": datetime.now()
    }
    
    logger.info("🔄 Агент сброшен")
    
    return {
        "message": "Агент успешно сброшен",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/workspace", summary="Получить список файлов в рабочей директории")
async def list_workspace_files(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Возвращает список всех файлов в папке workspace."""
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(exist_ok=True)
    
    files = []
    for root, _, filenames in os.walk(workspace_dir):
        for name in filenames:
            file_path = Path(root) / name
            rel_path = file_path.relative_to(workspace_dir)
            files.append({
                "name": name,
                "path": str(rel_path).replace("\\", "/"),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
            
    return {
        "status": "success",
        "files": files,
        "total": len(files)
    }

@router.get("/sandbox/{session_id}/vnc", summary="Получить URL-адрес VNC для сессии")
async def get_sandbox_vnc(session_id: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Возвращает URL-адрес VNC для указанной сессии."""
    from backend.sandbox.singleton import sandbox_manager
    
    url = sandbox_manager.get_novnc_url(session_id)
    if not url:
        raise HTTPException(status_code=404, detail="VNC URL not found for session")
    
    return {
        "status": "success",
        "session_id": session_id,
        "url": url
    }


@router.get("/workspace/file", summary="Прочитать содержимое файла из workspace")
async def read_workspace_file(path: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Возвращает содержимое файла из workspace по относительному пути."""
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(exist_ok=True)
    
    # Normalize the path — strip leading slashes and sandbox prefixes
    clean_path = path.strip("/")
    # Handle paths that come from the container like /home/ubuntu/workspace/...
    for prefix in ["home/ubuntu/workspace/", "workspace/"]:
        if clean_path.startswith(prefix):
            clean_path = clean_path[len(prefix):]
    
    file_path = workspace_dir / clean_path
    
    # Security: prevent path traversal
    try:
        file_path = file_path.resolve()
        workspace_resolved = workspace_dir.resolve()
        if not str(file_path).startswith(str(workspace_resolved)):
            raise HTTPException(status_code=403, detail="Access denied: path traversal detected")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {clean_path}")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        ext = file_path.suffix.lstrip(".")
        lang_map = {
            "py": "python", "js": "javascript", "ts": "typescript", "tsx": "typescriptreact",
            "jsx": "javascriptreact", "html": "html", "css": "css", "json": "json",
            "md": "markdown", "yaml": "yaml", "yml": "yaml", "sh": "shell",
            "sql": "sql", "xml": "xml", "txt": "plaintext"
        }
        return {
            "status": "success",
            "path": clean_path,
            "filename": file_path.name,
            "content": content,
            "language": lang_map.get(ext, "plaintext"),
            "size": file_path.stat().st_size
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", summary="Загрузить файл в workspace")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Загружает файл в папку workspace фронтендом."""
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(exist_ok=True)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_location = workspace_dir / file.filename
    try:
        MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 50MB.")
        with open(file_location, "wb+") as file_object:
            file_object.write(contents)
            
        logger.info(f"📤 Загружен файл: {file.filename}")
        
        return {
            "status": "success",
            "message": f"Файл {file.filename} успешно загружен",
            "filename": file.filename,
            "path": str(file_location)
        }
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
