import asyncio
import json
import logging
import struct
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BROWSER_SOCKET_PORT = 9222  # Must match browser_server.py SOCKET_PORT


class NativeBrowserTool:
    """
    Native low-latency browser orchestrator.
    
    Two IPC modes (auto-selected):
    1. TCP socket (port 9222) — <5ms latency, preferred
    2. File-based polling — ~150ms latency, legacy fallback
    """
    def __init__(self):
        self.name = "browser"
        self._socket_connections: Dict[str, tuple] = {}  # session_id -> (reader, writer)

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "High-performance native browser interaction. Use this to navigate, click, type, scroll, or extract data from web pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["navigate", "click", "type", "type_and_submit", "scroll", "extract", "get_elements", "current_state", "inject_js"],
                            "description": "The browser action to perform."
                        },
                        "url": {"type": "string", "description": "URL to navigate to (required for navigate action)"},
                        "text": {"type": "string", "description": "Text to click, type, or extract (depending on action)"},
                        "selector": {"type": "string", "description": "CSS selector to interact with"},
                        "script": {"type": "string", "description": "JavaScript code to execute (for inject_js)"},
                        "query": {"type": "string", "description": "Query to extract from page content"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        logger.info(f"NativeBrowserTool: action='{action}' session='{session_id}'")
        
        payload = {"action": action}
        payload.update(kwargs)
        # Remove session_id from payload — it's not a browser action parameter
        payload.pop("session_id", None)

        # Try TCP socket first (fast path)
        result = await self._execute_via_socket(session_id, payload)
        if result is not None:
            return result

        # Fallback to file-based IPC (slow path)
        logger.info("Socket unavailable, falling back to file-based IPC")
        return await self._execute_via_file(session_id, payload)

    # ─── TCP Socket Path (<5ms latency) ──────────────────────────

    async def _get_socket_connection(self, session_id: str) -> Optional[tuple]:
        """Get or create a persistent TCP connection to the browser server."""
        # Check if existing connection is still alive
        if session_id in self._socket_connections:
            reader, writer = self._socket_connections[session_id]
            if not writer.is_closing():
                return reader, writer
            # Dead connection, remove it
            del self._socket_connections[session_id]

        # Resolve the container's mapped port for 9222
        try:
            from backend.sandbox.singleton import sandbox_manager
            session = sandbox_manager._sessions.get(session_id)
            if not session:
                return None

            container = session.container
            loop = asyncio.get_running_loop()

            def _get_port():
                container.reload()
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                browser_port = ports.get(f"{BROWSER_SOCKET_PORT}/tcp")
                if browser_port and len(browser_port) > 0:
                    return int(browser_port[0].get("HostPort", 0))
                return 0

            host_port = await loop.run_in_executor(None, _get_port)
            if not host_port:
                return None

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", host_port),
                timeout=3.0
            )
            self._socket_connections[session_id] = (reader, writer)
            logger.info(f"Socket connected to browser server at port {host_port}")
            return reader, writer

        except Exception as e:
            logger.debug(f"Socket connection failed: {e}")
            return None

    async def _execute_via_socket(self, session_id: str, payload: dict) -> Optional[Dict[str, Any]]:
        """Execute browser action via TCP socket. Returns None if socket unavailable."""
        conn = await self._get_socket_connection(session_id)
        if conn is None:
            return None

        reader, writer = conn
        try:
            # Length-prefixed JSON protocol
            data = json.dumps(payload).encode("utf-8")
            writer.write(struct.pack(">I", len(data)))
            writer.write(data)
            await writer.drain()

            # Read response
            length_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=35)
            msg_len = struct.unpack(">I", length_bytes)[0]
            response_bytes = await asyncio.wait_for(reader.readexactly(msg_len), timeout=35)
            return json.loads(response_bytes.decode("utf-8"))

        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError, OSError) as e:
            logger.warning(f"Socket connection lost: {e}")
            # Remove dead connection
            self._socket_connections.pop(session_id, None)
            try:
                writer.close()
            except Exception:
                pass
            return None
        except asyncio.TimeoutError:
            return {"success": False, "error": "Browser socket response timeout (35s)"}
        except Exception as e:
            logger.error(f"Socket execute error: {e}")
            return None

    # ─── File-Based Path (~150ms latency, legacy fallback) ───────

    async def _execute_via_file(self, session_id: str, payload: dict) -> Dict[str, Any]:
        """Execute browser action via file-based IPC inside the sandbox container."""
        try:
            from backend.sandbox.singleton import sandbox_manager

            json_payload = json.dumps(payload)

            # Clean up any leftover result file
            await sandbox_manager.executor.run_command(session_id, "rm -f /tmp/browser_res.json")

            # Write command via filesystem (avoids bash escaping issues)
            write_res = await sandbox_manager.filesystem.write_file(
                session_id, "/tmp/browser_cmd.json", json_payload
            )
            if not write_res.get("success"):
                return {"success": False, "error": f"Failed to write command: {write_res.get('error')}"}

            # Wait for result
            timeout = 35
            start_time = time.time()

            while time.time() - start_time < timeout:
                read_res = await sandbox_manager.filesystem.read_file(
                    session_id, "/tmp/browser_res.json"
                )
                if read_res.get("success"):
                    content = read_res["content"].strip()
                    if content:
                        try:
                            result_dict = json.loads(content)
                            await sandbox_manager.executor.run_command(
                                session_id, "rm -f /tmp/browser_res.json"
                            )
                            return result_dict
                        except json.JSONDecodeError:
                            pass  # File partially written, retry
                await asyncio.sleep(0.15)

            return {"success": False, "error": "Browser file-based response timeout (35s)"}

        except Exception as e:
            logger.error(f"File-based execute error: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_session(self, session_id: str):
        """Close socket connection for a destroyed session."""
        conn = self._socket_connections.pop(session_id, None)
        if conn:
            _, writer = conn
            try:
                writer.close()
            except Exception:
                pass
