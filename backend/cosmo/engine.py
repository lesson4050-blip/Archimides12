"""
COSMO Presentation Engine Manager
Starts and manages the Presenton-based generation engine
as an internal subprocess. Port 5051, internal only.
It also starts the Next.js visual artist on Port 3005.
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

ARTIST_PORT = 3005
ARTIST_DIR = Path(__file__).parent.parent.parent / "cosmo_engine" / "designer"

_process: subprocess.Popen = None
_artist_process: subprocess.Popen = None


async def start_engine():
    """Start COSMO engine and Artist subprocesses on startup."""
    global _process, _artist_process
    
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
        "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "qwen2.5:14b"),
        # Pexels for images (free) — fallback to Pollinations
        "IMAGE_PROVIDER": os.environ.get("IMAGE_PROVIDER", "pexels"),
        "PEXELS_API_KEY": os.environ.get("PEXELS_API_KEY", ""),
        "APP_NAME": "COSMO Presentation",
        "APP_DATA_DIRECTORY": str(ENGINE_DIR / "data"),
        "DATABASE_URL": "sqlite+aiosqlite:///presenton.db",
    }
    
    (ENGINE_DIR / "data").mkdir(parents=True, exist_ok=True)

    try:
        # Start Backend (Brain)
        _process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "api.main:app",
                "--host", "127.0.0.1",
                "--port", str(ENGINE_PORT),
                "--log-level", "info"
            ],
            cwd=str(ENGINE_DIR),
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Start Next.js Frontend (Artist)
        if ARTIST_DIR.exists():
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            logger.info("Starting Next.js Artist on port 3005...")
            artist_env = os.environ.copy()
            artist_env["TEMP_DIRECTORY"] = str(ENGINE_DIR / "data" / "temp")
            artist_env["NEXT_PUBLIC_COSMO_ENGINE_URL"] = f"http://localhost:{ENGINE_PORT}"
            artist_env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{ENGINE_PORT}"
            artist_env["NODE_ENV"] = "development"
            
            _artist_process = subprocess.Popen(
                [npm_cmd, "run", "dev", "--", "-p", str(ARTIST_PORT)],
                cwd=str(ARTIST_DIR),
                env=artist_env,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
        else:
            logger.warning(f"Artist directory not found at {ARTIST_DIR}")

        # Wait up to 10 minutes for engine to be ready (model downloads)
        for i in range(1200):
            await asyncio.sleep(0.5)
            if await _health_check():
                logger.info(
                    f"COSMO Presentation engine started "
                    f"on port {ENGINE_PORT} (Artist on port 3005)"
                )
                return True

        logger.error("COSMO engine failed to start in 10m")
        return False

    except Exception as e:
        logger.error(f"COSMO engine start error: {e}")
        return False


async def stop_engine():
    """Stop engine and artist on shutdown."""
    global _process, _artist_process
    
    if _process:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
        logger.info("COSMO engine stopped")
        
    if _artist_process:
        _artist_process.terminate()
        try:
            _artist_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _artist_process.kill()
        _artist_process = None
        logger.info("COSMO artist stopped")


async def _health_check() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            r = await c.get(f"{ENGINE_URL}/health")
            # Artist might take longer to compile, but main health is via uvicorn
            return r.status_code == 200
    except Exception:
        return False


def get_engine_url() -> str:
    return ENGINE_URL
