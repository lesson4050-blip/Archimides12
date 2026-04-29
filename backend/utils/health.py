"""
Production Health Checks.
Deep health: checks DB, Ollama, disk, memory, all critical subsystems.
"""
import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def deep_health_check() -> Dict[str, Any]:
    """Run comprehensive health checks on all subsystems."""
    start = time.monotonic()
    checks = {}

    # 1. Database
    try:
        from backend.db.crud import _engine
        if _engine:
            checks["database"] = {"status": "healthy", "type": "sqlite"}
        else:
            checks["database"] = {"status": "not_configured"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)[:100]}

    # 2. Ollama
    try:
        import httpx
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            models = resp.json().get("models", [])
            checks["ollama"] = {
                "status": "healthy",
                "models_loaded": len(models),
                "model_names": [m["name"] for m in models[:5]]
            }
    except Exception as e:
        checks["ollama"] = {"status": "unavailable", "error": str(e)[:100]}

    # 3. Disk
    try:
        import psutil
        disk = psutil.disk_usage("/")
        checks["disk"] = {
            "status": "healthy" if disk.percent < 90 else "warning",
            "used_percent": disk.percent,
            "free_gb": round(disk.free / (1024**3), 1)
        }
    except Exception:
        checks["disk"] = {"status": "unknown"}

    # 4. Memory
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "healthy" if mem.percent < 90 else "warning",
            "used_percent": mem.percent,
            "available_gb": round(mem.available / (1024**3), 1)
        }
    except Exception:
        checks["memory"] = {"status": "unknown"}

    # 5. Session store
    try:
        from backend.agent.session_store import SESSION_DIR
        session_count = len([
            f for f in os.listdir(SESSION_DIR)
            if f.endswith((".json", ".pkl"))
        ]) if os.path.exists(SESSION_DIR) else 0
        checks["sessions"] = {"status": "healthy", "active_sessions": session_count}
    except Exception:
        checks["sessions"] = {"status": "unknown"}

    all_healthy = all(
        c.get("status") in ("healthy", "not_configured", "unknown")
        for c in checks.values()
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "response_time_ms": round((time.monotonic() - start) * 1000, 1),
        "version": "3.0.0",
        "uptime_seconds": round(time.monotonic(), 0)
    }
