"""
COSMO Artist Server Manager
Starts Presenton Next.js as headless API server on port 3005.
This provides: template layouts, PPTX rendering, PDF export.
The Archimedes frontend (port 3000) is separate.
Artist UI is NOT accessible to users — API only.
"""
import asyncio
import logging
import os
import subprocess
import sys
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

ARTIST_PORT = int(os.environ.get("COSMO_ARTIST_PORT", "3005"))
ARTIST_URL = f"http://127.0.0.1:{ARTIST_PORT}"
ARTIST_DIR = Path(__file__).parent.parent.parent / "cosmo_artist"

_process: subprocess.Popen = None


async def start_artist():
    """Start Next.js Artist server as headless API."""
    global _process
    if _process and _process.poll() is None:
        logger.info("COSMO Artist already running")
        return True

    if not ARTIST_DIR.exists():
        logger.error(f"cosmo_artist/ not found at {ARTIST_DIR}")
        logger.error(
            "Run: git clone https://github.com/presenton/presenton.git tmp && "
            "cp -r tmp/servers/nextjs cosmo_artist && rm -rf tmp && "
            "cd cosmo_artist && npm install && npm run build && cd .."
        )
        return False

    # Check if built
    build_dir = ARTIST_DIR / ".next"
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    if not build_dir.exists():
        logger.info("Building COSMO Artist (first time)...")
        result = subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=str(ARTIST_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            logger.error(f"Artist build failed: {result.stderr[:500]}")
            return False
        logger.info("COSMO Artist built successfully")

    engine_port = os.environ.get('COSMO_ENGINE_PORT', '5051')
    temp_dir = str(ARTIST_DIR.parent / "cosmo_engine_core" / "data" / "temp")
    os.makedirs(temp_dir, exist_ok=True)

    env = {
        **os.environ,
        "PORT": str(ARTIST_PORT),
        "NODE_ENV": "production",
        # Point Artist to our COSMO engine (for schema/pdf-maker pages)
        # NEXT_PUBLIC_FAST_API is the key one — it's read by getApiUrl() client-side
        "NEXT_PUBLIC_FAST_API": f"http://127.0.0.1:{engine_port}",
        "NEXT_PUBLIC_SERVER_URL": f"http://127.0.0.1:{engine_port}",
        "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{engine_port}",
        "NEXT_PUBLIC_COSMO_ENGINE_URL": f"http://127.0.0.1:{engine_port}",
        # Temp dir for screenshots during PPTX rendering
        "TEMP_DIRECTORY": temp_dir,
        # Disable telemetry
        "NEXT_TELEMETRY_DISABLED": "1",
    }

    try:
        _process = subprocess.Popen(
            [npm_cmd, "start", "--", "--port", str(ARTIST_PORT)],
            cwd=str(ARTIST_DIR),
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        # Wait up to 90s for server ready (Puppeteer first call is slow)
        for _ in range(180):
            await asyncio.sleep(0.5)
            if await _health_check_simple():
                logger.info(
                    f"COSMO Artist server ready at port {ARTIST_PORT}"
                )
                return True

        logger.error("COSMO Artist failed to start in 90s")
        return False

    except Exception as e:
        logger.error(f"Artist start error: {e}")
        return False


async def stop_artist():
    global _process
    if _process:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
        logger.info("COSMO Artist stopped")


async def _health_check_simple() -> bool:
    """Quick check — just verify Next.js process is listening."""
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            # Use a lightweight endpoint, not template (which triggers Puppeteer)
            r = await c.get(f"{ARTIST_URL}/api/telemetry-status")
            return r.status_code in (200, 404)  # 404 is fine, means server is up
    except Exception:
        return False


async def _health_check_full() -> bool:
    """Full check — verify template API works (triggers Puppeteer)."""
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(f"{ARTIST_URL}/api/template?group=general")
            return r.status_code == 200
    except Exception:
        return False


def get_artist_url() -> str:
    return ARTIST_URL
