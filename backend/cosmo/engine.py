"""
COSMO Presentation Engine Manager
Starts and manages the Presenton-based generation engine
as an internal subprocess. Port 5051, internal only.
"""
import asyncio
import logging
import os
import sys
import subprocess
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

ENGINE_PORT = int(os.environ.get("COSMO_ENGINE_PORT", "5051"))
ENGINE_URL = f"http://127.0.0.1:{ENGINE_PORT}"
ENGINE_DIR = Path(__file__).parent.parent.parent / "cosmo_engine_core"

_process: subprocess.Popen = None


async def start_engine():
    """Start COSMO engine subprocess on startup."""
    global _process
    if _process and _process.poll() is None:
        logger.info("COSMO engine already running")
        return True

    if not ENGINE_DIR.exists():
        logger.error(f"COSMO engine not found at {ENGINE_DIR}")
        return False

    env = {
        **os.environ,
        "PORT": str(ENGINE_PORT),
        "HOST": "127.0.0.1",
        # Use Ollama as default — no API key needed
        "LLM": os.environ.get("LLM", "ollama"),
        "OLLAMA_HOST": os.environ.get(
            "OLLAMA_HOST", "http://localhost:11434"
        ),
        "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "gemma4:26b"),
        # Pexels for images (free) — fallback to Pollinations
        "IMAGE_PROVIDER": os.environ.get("IMAGE_PROVIDER", "pexels"),
        "PEXELS_API_KEY": os.environ.get("PEXELS_API_KEY", ""),
        "APP_NAME": "COSMO Presentation",
        "APP_DATA_DIRECTORY": str(ENGINE_DIR / "data"),
        "DATABASE_URL": "sqlite+aiosqlite:///presenton.db",
    }
    
    (ENGINE_DIR / "data").mkdir(parents=True, exist_ok=True)

    try:
        _process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "api.main:app",
                "--host", "127.0.0.1",
                "--port", str(ENGINE_PORT),
                "--log-level", "error"
            ],
            cwd=str(ENGINE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        # Wait up to 10 minutes for engine to be ready (model downloads)
        for i in range(1200):
            await asyncio.sleep(0.5)
            if await _health_check():
                logger.info(
                    f"COSMO Presentation engine started "
                    f"on port {ENGINE_PORT}"
                )
                return True

        logger.error("COSMO engine failed to start in 10m")
        return False

    except Exception as e:
        logger.error(f"COSMO engine start error: {e}")
        return False


async def stop_engine():
    """Stop engine on shutdown."""
    global _process
    if _process:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
        logger.info("COSMO engine stopped")


async def _health_check() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            r = await c.get(f"{ENGINE_URL}/health")
            return r.status_code == 200
    except Exception:
        return False


def get_engine_url() -> str:
    return ENGINE_URL
