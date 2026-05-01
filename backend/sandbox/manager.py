from backend.utils.task import safe_create_task
import docker
import logging
import asyncio
import os
import sys
import time
import json
import shutil
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


@dataclass
class Snapshot:
    """A point-in-time snapshot of the sandbox filesystem."""
    snapshot_id: str
    session_id: str
    created_at: float
    description: str = ""
    files_captured: int = 0
    size_bytes: int = 0


class SnapshotManager:
    """
    Replit-style filesystem snapshots for safe agent operations.
    Creates snapshots before destructive operations, allows instant rollback.
    """

    SNAPSHOT_DIR = "data/snapshots"
    MAX_SNAPSHOTS_PER_SESSION = 20

    def __init__(self):
        os.makedirs(self.SNAPSHOT_DIR, exist_ok=True)
        self._snapshots: Dict[str, List[Snapshot]] = {}

    async def create_snapshot(
        self, session_id: str, workspace_path: str, description: str = ""
    ) -> Optional[Snapshot]:
        """Create a snapshot of the current workspace state."""
        snapshot_id = f"snap_{session_id}_{int(time.time())}"
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, snapshot_id)

        try:
            os.makedirs(snapshot_path, exist_ok=True)
            manifest = {}
            file_count = 0
            total_size = 0

            for root, dirs, files in os.walk(workspace_path):
                dirs[:] = [d for d in dirs if d not in {
                    '.git', 'node_modules', '__pycache__', 'venv',
                    '.venv', 'dist', 'build', '.next', 'data'
                }]
                for filename in files:
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, workspace_path)
                    try:
                        stat = os.stat(filepath)
                        if stat.st_size > 10 * 1024 * 1024:
                            continue
                        dest = os.path.join(snapshot_path, rel_path)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(filepath, dest)
                        manifest[rel_path] = {"size": stat.st_size, "mtime": stat.st_mtime}
                        file_count += 1
                        total_size += stat.st_size
                    except (PermissionError, OSError):
                        continue

            with open(os.path.join(snapshot_path, ".manifest.json"), "w") as f:
                json.dump(manifest, f)

            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                session_id=session_id,
                created_at=time.time(),
                description=description,
                files_captured=file_count,
                size_bytes=total_size,
            )

            if session_id not in self._snapshots:
                self._snapshots[session_id] = []
            self._snapshots[session_id].append(snapshot)

            # Auto-rotation
            if len(self._snapshots[session_id]) > self.MAX_SNAPSHOTS_PER_SESSION:
                oldest = self._snapshots[session_id].pop(0)
                self._cleanup_snapshot(oldest.snapshot_id)

            logger.info(f"Snapshot created: {snapshot_id} ({file_count} files)")
            return snapshot

        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")
            return None

    async def rollback(
        self, session_id: str, snapshot_id: str, workspace_path: str
    ) -> bool:
        """Restore workspace to a previous snapshot."""
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, snapshot_id)
        if not os.path.exists(snapshot_path):
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        try:
            manifest_path = os.path.join(snapshot_path, ".manifest.json")
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            restored = 0
            for rel_path in manifest:
                src = os.path.join(snapshot_path, rel_path)
                dst = os.path.join(workspace_path, rel_path)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    restored += 1

            logger.info(f"Rollback complete: {snapshot_id} ({restored} files restored)")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def list_snapshots(self, session_id: str) -> List[Snapshot]:
        return self._snapshots.get(session_id, [])

    def _cleanup_snapshot(self, snapshot_id: str):
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, snapshot_id)
        if os.path.exists(snapshot_path):
            shutil.rmtree(snapshot_path, ignore_errors=True)

    def cleanup_session(self, session_id: str):
        for snap in self._snapshots.get(session_id, []):
            self._cleanup_snapshot(snap.snapshot_id)
        self._snapshots.pop(session_id, None)


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
        self.snapshots = SnapshotManager()

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
            self._reaper_task = safe_create_task(self._reaper_loop())
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
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
                try:
                    c.remove(force=True)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
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
                session_workspace = os.path.abspath(f"./workspace/{session_id}")
                os.makedirs(session_workspace, exist_ok=True)

                return client.containers.run(
                    settings.SANDBOX_IMAGE,
                    name=container_name,
                    hostname=f"sandbox-{session_id}",
                    mem_limit="2g",
                    cpu_quota=100000,  # 1 CPU
                    security_opt=["no-new-privileges:true"],
                    cap_drop=["ALL"],
                    cap_add=["CHOWN", "SETUID", "SETGID"],
                    environment={"SESSION_ID": session_id},
                    volumes={
                        session_workspace: {"bind": "/home/ubuntu/workspace", "mode": "rw"},
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
            safe_create_task(self.novnc.start_streaming(session_id))

            # Create workspace dir
            await loop.run_in_executor(
                None,
                lambda: container.exec_run("chown -R ubuntu:ubuntu /home/ubuntu/workspace")
            )
            
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
        try:
            await loop.run_in_executor(None, lambda: container.remove(force=True))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
            
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