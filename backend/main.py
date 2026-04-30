from backend.utils.task import safe_create_task
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.websocket.handler import manager
from backend.sandbox.singleton import sandbox_manager
from backend.db.crud import init_db
from backend.api.routes import router as main_router
from backend.auth.routes import router as auth_router
from backend.api.settings_routes import router as settings_router
from backend.api.connectors_router import router as connectors_router
from backend.api.quick_task_router import router as quick_task_router
from backend.api.benchmark import router as benchmark_router
from backend.api.streaming import router as streaming_router

self_play_loop_instance = None


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Archimedes Backend starting up...")
    
    # Configure correlated observability (session_id + trace_id in all logs)
    try:
        from backend.utils.observability import configure_json_logging
        configure_json_logging()
        logger.info("Observability initialized (LOG_FORMAT detection active)")
    except Exception as e:
        logger.warning(f"Observability setup failed (non-critical): {e}")
    
    if settings.AUTH_ENABLED:
        if not settings.JWT_SECRET_KEY:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: JWT_SECRET_KEY is not set in .env. "
                "In production, this allows trivial token forgery. "
                "Set JWT_SECRET_KEY in .env using: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        if len(settings.JWT_SECRET_KEY) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: JWT_SECRET_KEY is too short (must be at least 32 characters). "
                "Please generate a stronger key."
            )
    else:
        logger.warning("Authentication is DISABLED. This is insecure for production use.")
    
    await init_db()

    # Clean up stale containers from previous runs
    sandbox_manager.cleanup_stale_containers()

    # Preload Ollama model to eliminate cold start
    async def _preload_model():
        try:
            import ollama
            import asyncio
            client = ollama.AsyncClient(
                host=settings.OLLAMA_BASE_URL, timeout=120
            )
            await client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                options={"num_predict": 1, "keep_alive": "30m"}
            )
            logger.info(f"Model {settings.OLLAMA_MODEL} preloaded")
        except Exception as e:
            logger.warning(f"Model preload failed (non-critical): {e}")

    import asyncio
    safe_create_task(_preload_model())

    # Start the inactivity reaper
    sandbox_manager.start_reaper()
    
    # Start Self-Play Loop
    from backend.agent.self_play_loop import SelfPlayLoop
    from backend.models.model_router import ModelRouter
    from backend.agent.skill_library import SkillLibrary
    
    global self_play_loop_instance
    self_play_loop_instance = SelfPlayLoop(
        router=ModelRouter(),
        skill_library=SkillLibrary(),
        idle_threshold_mins=30
    )
    safe_create_task(self_play_loop_instance.start())
    logger.info("SelfPlayLoop starting...")
    
    # Start the scheduler
    from backend.tools.scheduler_singleton import get_scheduler
    get_scheduler().start()
    
    # Start COSMO Presentation engine
    from backend.cosmo.engine import start_engine, stop_engine
    safe_create_task(start_engine())
    logger.info("COSMO Presentation engine starting...")

    # ChromaDB Monitoring Task
    async def _monitor_chroma():
        from backend.memory.vector_store import VectorStore
        store = VectorStore()
        while True:
            stats = store.get_collection_stats()
            count = stats.get("count", 0)
            if count > 500000:
                logger.error(f"ChromaDB Growth Bomb: Collection has {count} documents! Performance will severely degrade.")
            elif count > 100000:
                logger.warning(f"ChromaDB Warning: Collection has {count} documents. Consider cleanup.")
            
            await asyncio.sleep(3600) # Check every hour

    safe_create_task(_monitor_chroma())

    # Start COSMO Artist (Next.js template server)
    from backend.cosmo.artist import start_artist, stop_artist as stop_artist_fn
    artist_task = safe_create_task(start_artist())
    logger.info("COSMO Artist server starting on port 3005...")
    
    logger.info(f"Auth: {'ENABLED' if settings.AUTH_ENABLED else 'DISABLED (dev mode)'}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Playwright binary check
    try:
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "playwright", "help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if process.returncode != 0:
            logger.warning("Playwright may not be installed. Presentation rendering limits will apply.")
    except Exception:
        logger.warning("Playwright check failed. Run `pip install playwright` and `playwright install` to enable PDF generation.")

    yield

    # Shutdown
    logger.info("Archimedes Backend shutting down... Cleaning up sandboxes.")

    # Section 7A: Graceful shutdown for all background tasks
    from backend.websocket.handler import manager as ws_manager
    for session_id, agent in list(ws_manager.agent_loops.items()):
        try:
            if hasattr(agent, 'mcp_client'):
                for server_name in list(
                    getattr(agent.mcp_client, '_stop_events', {}).keys()
                ):
                    try:
                        await agent.mcp_client.disconnect_server(server_name)
                    except Exception as e:
                        logger.warning(f"Failed to disconnect MCP server {server_name}: {e}")
        except Exception as e:
            logger.warning(f"Error during MCP cleanup for {session_id}: {e}")

    sandbox_manager.stop_reaper()
    
    if self_play_loop_instance:
        self_play_loop_instance.stop()

    await sandbox_manager.cleanup()
    await stop_engine()
    await stop_artist_fn()

app = FastAPI(
    title="Archimedes API",
    description="Backend for the Archimedes Autonomous AI Agent",
    lifespan=lifespan
)

import os

ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
).split(",")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Session-ID"],
)

# Phase 3: Security middleware
from backend.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth_router)
app.include_router(main_router)
app.include_router(settings_router)
app.include_router(connectors_router)
app.include_router(quick_task_router)
app.include_router(benchmark_router)
app.include_router(streaming_router)



@app.get("/")
async def root():
    return {"message": "Archimedes API is running."}


@app.get("/api/health")
async def api_health():
    """Top-level health check with real component status."""
    from datetime import datetime

    # Check DB
    db_ok = False
    try:
        from backend.db.crud import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Check Ollama
    ollama_ok = False
    try:
        import ollama
        client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        await client.list()
        ollama_ok = True
    except Exception:
        pass

    # Check Memory Bank
    memory_ok = False
    try:
        from backend.memory.memory_bank import get_relevant_facts
        facts = await get_relevant_facts(limit=1)
        memory_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0-beyond-manus",
        "components": {
            "database": "ok" if db_ok else "error",
            "ollama": "ok" if ollama_ok else "error",
            "memory_bank": "ok" if memory_ok else "error",
        }
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # Phase 3: Validate session_id format
    from backend.middleware.security import validate_session_id
    if not validate_session_id(session_id):
        await websocket.close(code=4001, reason="Invalid session_id format")
        return

    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(session_id, data)
    except WebSocketDisconnect:
        await manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        await manager.disconnect(session_id)

@app.get(\"/api/health/models\")
async def model_health():
    from backend.models.model_router import ModelRouter
    router = ModelRouter()
    return await router.get_health_status()

if __name__ == \"__main__\":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)