"""
КОСМО-уровневый WebSocket обработчик для реал-тайм коммуникации.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Управление WebSocket соединениями."""

    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
        self.message_queue: Dict[str, asyncio.Queue] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket, client_id: str) -> None:
        """Подключить клиента."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.message_queue[client_id] = asyncio.Queue()
        self.session_data[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "messages_sent": 0,
            "messages_received": 0
        }
        logger.info(f"✅ Клиент подключен: {client_id}")

    def disconnect(self, client_id: str) -> None:
        """Отключить клиента."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.message_queue:
            del self.message_queue[client_id]
        logger.info(f"❌ Клиент отключен: {client_id}")

    async def send_personal(self, client_id: str, message: Dict[str, Any]) -> None:
        """Отправить личное сообщение."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
                self.session_data[client_id]["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {str(e)}")

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[str] = None) -> None:
        """Отправить сообщение всем клиентам."""
        for client_id, websocket in self.active_connections.items():
            if exclude and client_id == exclude:
                continue
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Ошибка трансляции: {str(e)}")

    async def receive_message(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Получить сообщение от клиента."""
        if client_id in self.message_queue:
            try:
                message = await asyncio.wait_for(
                    self.message_queue[client_id].get(),
                    timeout=300.0
                )
                self.session_data[client_id]["messages_received"] += 1
                return message
            except asyncio.TimeoutError:
                return None
        return None

    def get_connected_clients(self) -> Dict[str, Any]:
        """Получить информацию о подключенных клиентах."""
        return {
            client_id: {
                "connected_at": self.session_data[client_id]["connected_at"],
                "messages_sent": self.session_data[client_id]["messages_sent"],
                "messages_received": self.session_data[client_id]["messages_received"]
            }
            for client_id in self.active_connections.keys()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику соединений."""
        total_messages = sum(
            data["messages_sent"] + data["messages_received"]
            for data in self.session_data.values()
        )
        
        return {
            "active_connections": len(self.active_connections),
            "total_messages": total_messages,
            "clients": self.get_connected_clients()
        }


class MessageHandler:
    """Обработчик сообщений WebSocket."""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.handlers: Dict[str, callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Зарегистрировать встроенные обработчики."""
        self.register("ping", self._handle_ping)
        self.register("status", self._handle_status)
        self.register("task", self._handle_task)
        self.register("query", self._handle_query)

    def register(self, message_type: str, handler: callable) -> None:
        """Зарегистрировать обработчик сообщения."""
        self.handlers[message_type] = handler
        logger.info(f"📨 Обработчик зарегистрирован: {message_type}")

    async def handle_message(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработать входящее сообщение."""
        try:
            message_type = message.get("type", "unknown")
            
            if message_type in self.handlers:
                handler = self.handlers[message_type]
                response = await handler(client_id, message)
            else:
                response = {
                    "type": "error",
                    "error": f"Неизвестный тип сообщения: {message_type}"
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
            return {
                "type": "error",
                "error": str(e)
            }

    async def _handle_ping(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработчик ping."""
        return {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id
        }

    async def _handle_status(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработчик запроса статуса."""
        return {
            "type": "status",
            "data": self.manager.get_statistics(),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_task(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработчик задачи."""
        task_id = str(uuid.uuid4())
        task_data = message.get("data", {})
        
        return {
            "type": "task_accepted",
            "task_id": task_id,
            "status": "queued",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_query(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработчик запроса."""
        query = message.get("query", "")
        
        return {
            "type": "query_response",
            "query": query,
            "result": f"Ответ на запрос: {query}",
            "timestamp": datetime.now().isoformat()
        }


class CosmoWebSocketManager:
    """Главный менеджер WebSocket для КОСМО."""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.message_handler = MessageHandler(self.connection_manager)
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

    async def handle_client(self, websocket, client_id: str) -> None:
        """Обработать клиента."""
        await self.connection_manager.connect(websocket, client_id)
        
        try:
            while True:
                # Получить сообщение от клиента
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Обработать сообщение
                response = await self.message_handler.handle_message(client_id, message)
                
                # Отправить ответ
                await self.connection_manager.send_personal(client_id, response)
                
        except Exception as e:
            logger.error(f"Ошибка обработки клиента: {str(e)}")
        finally:
            self.connection_manager.disconnect(client_id)

    async def broadcast_status(self, status: Dict[str, Any]) -> None:
        """Трансляция статуса всем клиентам."""
        message = {
            "type": "status_update",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.broadcast(message)

    async def broadcast_task_update(self, task_id: str, update: Dict[str, Any]) -> None:
        """Трансляция обновления задачи."""
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.broadcast(message)

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику WebSocket."""
        return {
            "connections": self.connection_manager.get_statistics(),
            "active_tasks": len(self.active_tasks)
        }


# Глобальный менеджер
ws_manager = CosmoWebSocketManager()
