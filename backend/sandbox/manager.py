import docker
import logging
import asyncio
import os
import sys
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from backend.config import settings
from backend.sandbox.executor import SandboxExecutor, PersistentShell
from backend.sandbox.filesystem import SandboxFilesystem
from backend.sandbox.novnc import NoVNCManager

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Tracks a single session's container and activity."""
    container: Any
    session_id: str
    last_activity: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


class SandboxManager:
    """
    Manages the lifecycle of Docker containers used as sandboxes.
    Manus-style: one container per user session (not per request).

    - Container created when a new session starts (WebSocket connects)
    - Same container reused for ALL tasks within that session
    - Container deleted when session ends (WebSocket disconnects or inactivity timeout)
    - Max containers enforced with queuing
    """

    def __init__(self):
        self._client = None
        self._sessions: Dict[str, SessionInfo] = {}
        self._queue: List[asyncio.Event] = []
        self._queue_session_ids: List[str] = []
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task] = None
        
        self._shells: Dict[str, PersistentShell] = {}

        self.executor = SandboxExecutor(self)
        self.filesystem = SandboxFilesystem(self)
        self.novnc = NoVNCManager(self.executor)

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as e:
                logger.info(f"docker.from_env() failed ({e}), trying Windows pipe...")
                try:
                    self._client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
                    self._client.ping()
                except Exception as e2:
                    logger.error(f"Failed to connect to Docker on any endpoint: {e2}")
                    self._client = None
        return self._client

    # ------------------------------------------------------------------
    # Startup / Shutdown
    # ------------------------------------------------------------------

    def start_reaper(self):
        """Start the background inactivity reaper. Call from app startup."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())
            logger.info("Inactivity reaper started.")

    def stop_reaper(self):
        """Stop the background inactivity reaper. Call from app shutdown."""
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            logger.info("Inactivity reaper stopped.")

    def cleanup_stale_containers(self):
        """Remove any lingering archimedes-session-* containers from previous runs."""
        client = self.client
        if not client:
            return
        try:
            stale = client.containers.list(all=True, filters={"name": "archimedes-session-"})
            for c in stale:
                logger.info(f"Cleaning up stale container: {c.name}")
                try:
                    c.stop(timeout=5)
                except Exception:
                    pass
                try:
                    c.remove(force=True)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Stale container cleanup error: {e}")

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    async def create_session(self, session_id: str) -> bool:
        """
        Create a sandbox container for a new session.
        If max containers reached, the caller is queued and this method blocks
        until a slot opens. Returns True on success, False on failure.
        """
        async with self._lock:
            # Already exists? Just touch and return.
            if session_id in self._sessions:
                self._sessions[session_id].last_activity = time.time()
                logger.info(f"Session {session_id} already exists, reusing.")
                return True

            active_count = len(self._sessions)
            if active_count >= settings.SANDBOX_MAX_CONTAINERS:
                # Evict oldest session instead of queueing infinitely
                oldest_sid = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_activity)
                logger.info(f"Max containers reached. Evicting oldest session {oldest_sid} to make room for {session_id}.")
                session_to_evict = self._sessions.pop(oldest_sid)
                await self._stop_and_remove(session_to_evict.container, oldest_sid)

            # Create container immediately
            return await self._create_container(session_id)

    async def destroy_session(self, session_id: str):
        """
        Destroy a session's container. Called on WS disconnect or inactivity timeout.
        Frees a slot and wakes the next queued session if any.
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await self._stop_and_remove(session.container, session_id)

            # Wake next queued session
            self._wake_next_queued()

    def touch_session(self, session_id: str):
        """Update last_activity timestamp. Called on every tool/message."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()

    async def get_container(self, session_id: str) -> Optional[Any]:
        """
        Return the running container for a session.
        Unlike the old implementation, this does NOT create containers —
        creation happens in create_session().
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"get_container called for unknown session {session_id}")
            return None

        self.touch_session(session_id)

        container = session.container
        try:
            container.reload()
            if container.status == "running":
                return container
            else:
                logger.info(f"Container for session {session_id} stopped. Restarting...")
                container.start()
                return container
        except Exception as e:
            logger.error(f"Container for session {session_id} is invalid: {e}")
            return None

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    @property
    def queued_session_count(self) -> int:
        return len(self._queue)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _create_container(self, session_id: str) -> bool:
        """Create the Docker container and register the session. Caller must hold _lock."""
        client = self.client
        if not client:
            logger.error("Docker client not available.")
            return False

        container_name = f"archimedes-session-{session_id}"

        # Ensure image exists safely using run_in_executor
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: client.images.get(settings.SANDBOX_IMAGE))
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image {settings.SANDBOX_IMAGE}...")
            await loop.run_in_executor(None, lambda: client.images.pull(settings.SANDBOX_IMAGE))

        logger.info(f"Creating container {container_name} for session {session_id}")
        try:
            def _create_container_sync():
                return client.containers.run(
                    settings.SANDBOX_IMAGE,
                    name=container_name,
                    hostname=f"sandbox-{session_id}",
                    mem_limit="2g",
                    cpu_quota=100000,  # 1 CPU
                    environment={"SESSION_ID": session_id},
                    volumes={
                        os.path.abspath("./workspace"): {"bind": "/home/ubuntu/workspace", "mode": "rw"},
                        **({"vnc-data": {"bind": "/home/ubuntu/vnc", "mode": "rw"}} if sys.platform != "win32" else {})
                    },
                    ports={"6080/tcp": None},
                    detach=True,
                    tty=True,
                )
            
            container = await loop.run_in_executor(None, _create_container_sync)
            self._sessions[session_id] = SessionInfo(
                container=container,
                session_id=session_id,
            )

            # Start noVNC inside the container
            asyncio.create_task(self.novnc.start_streaming(session_id))

            # Create workspace dir
            container.exec_run("chown -R ubuntu:ubuntu /home/ubuntu/workspace")
            
            # Start persistent shell
            shell = PersistentShell(container)
            await shell.start()
            self._shells[session_id] = shell

            logger.info(
                f"Container {container_name} running. "
                f"Active: {len(self._sessions)}/{settings.SANDBOX_MAX_CONTAINERS}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return False

    def get_novnc_url(self, session_id: str) -> Optional[str]:
        """Get the VNC URL for the host to expose to the frontend."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        try:
            session.container.reload()
            ports = session.container.attrs.get('NetworkSettings', {}).get('Ports', {})
            novnc_port = ports.get('6080/tcp')
            if novnc_port and len(novnc_port) > 0:
                host_port = novnc_port[0].get('HostPort')
                return f"http://localhost:{host_port}/vnc.html?autoconnect=true&reconnect=true"
        except Exception as e:
            logger.error(f"Failed to get novnc port: {e}")
        return None

    async def _stop_and_remove(self, container: Any, session_id: str):
        """Stop and remove a Docker container."""
        container_name = f"archimedes-session-{session_id}"
        
        loop = asyncio.get_running_loop()
        
        # Stop persistent shell cleanly to avoid socket leaks
        shell = self._shells.pop(session_id, None)
        if shell:
            shell.stop()
            
        try:
            await loop.run_in_executor(None, lambda: container.stop(timeout=10))
        except Exception:
            pass
        try:
            await loop.run_in_executor(None, lambda: container.remove(force=True))
        except Exception:
            pass
            
        logger.info(
            f"Destroyed container {container_name}. "
            f"Active: {len(self._sessions)}/{settings.SANDBOX_MAX_CONTAINERS}"
        )

    def _wake_next_queued(self):
        """Wake the next queued session if there is capacity."""
        if self._queue and len(self._sessions) < settings.SANDBOX_MAX_CONTAINERS:
            event = self._queue.pop(0)
            queued_id = self._queue_session_ids.pop(0)
            logger.info(f"Waking queued session {queued_id}. Slot available.")
            event.set()

    # ------------------------------------------------------------------
    # Inactivity Reaper
    # ------------------------------------------------------------------

    async def _reaper_loop(self):
        """Background task: every 60s, destroy sessions idle longer than the timeout."""
        logger.info(
            f"Reaper running. Timeout = {settings.SANDBOX_INACTIVITY_TIMEOUT}s, "
            f"check interval = 60s."
        )
        try:
            while True:
                await asyncio.sleep(60)
                await self._reap_inactive()
        except asyncio.CancelledError:
            logger.info("Reaper task cancelled.")

    async def _reap_inactive(self):
        """Check all sessions and destroy any that exceeded the inactivity timeout."""
        now = time.time()
        timeout = settings.SANDBOX_INACTIVITY_TIMEOUT
        to_reap: List[str] = []

        for sid, info in self._sessions.items():
            idle = now - info.last_activity
            if idle > timeout:
                logger.info(
                    f"Session {sid} idle for {idle:.0f}s (>{timeout}s). Reaping."
                )
                to_reap.append(sid)

        for sid in to_reap:
            await self.destroy_session(sid)

    # ------------------------------------------------------------------
    # Full Cleanup (shutdown)
    # ------------------------------------------------------------------

    async def cleanup(self):
        """Stop and remove ALL active session containers. Called on app shutdown."""
        for session_id, session in list(self._sessions.items()):
            await self._stop_and_remove(session.container, session_id)
        self._sessions.clear()

        # Wake any queued sessions so they don't hang forever
        for event in self._queue:
            event.set()
        self._queue.clear()
        self._queue_session_ids.clear()
