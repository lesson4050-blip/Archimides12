import os
from backend.utils.task import safe_create_task
import logging
from contextlib import asynccontextmanager
from backend.metrics import http_request_duration_seconds, http_requests_total, generate_latest, CONTENT_TYPE_LATEST, active_websocket_connections
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time

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
from backend.telemetry import init_telemetry

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
    
    logger.info("Starting Self-Play Loop initialization...")
    # Start Self-Play Loop
    from backend.agent.self_play_loop import SelfPlayLoop
    from backend.models.model_router import ModelRouter
    from backend.agent.skill_library import SkillLibrary
    
    global self_play_loop_instance
    logger.info("Initializing ModelRouter and SkillLibrary...")
    self_play_loop_instance = SelfPlayLoop(
        router=ModelRouter(),
        skill_library=SkillLibrary(),
        idle_threshold_mins=30
    )
    logger.info("Starting SelfPlayLoop task...")
    safe_create_task(self_play_loop_instance.start())
    logger.info("SelfPlayLoop starting...")
    
    # Start the scheduler
    logger.info("Initializing Scheduler...")
    from backend.tools.scheduler_singleton import get_scheduler
    get_scheduler().start()
    
    # Start COSMO Presentation engine
    logger.info("Initializing COSMO Presentation engine...")
    try:
        from backend.cosmo.engine import start_engine, stop_engine
        safe_create_task(start_engine())
        logger.info("COSMO Presentation engine starting...")
    except ImportError:
        logger.warning("COSMO engine not found. Skipping.")

    # ChromaDB Monitoring Task
    async def _monitor_chroma():
        """Background task: monitor ALL ChromaDB collections every 5 minutes."""
        from backend.memory.vector_store import get_all_collections_stats, COLLECTION_MAX_DOCS
        from backend.metrics import chroma_user_collection_size, chroma_total_docs
        
        while True:
            try:
                await asyncio.sleep(300)  # every 5 minutes
                stats = await get_all_collections_stats()
                
                total = stats.get("total_docs", 0)
                chroma_total_docs.set(total)
                
                for col_stat in stats.get("collections", []):
                    user_id = col_stat["user_id"]
                    count = col_stat["count"]
                    chroma_user_collection_size.labels(user_id=user_id).set(count)
                    
                    # Warning at 80% of limit
                    if col_stat["utilization_pct"] > 80:
                        logger.warning(
                            f"ChromaDB: user '{user_id}' at {col_stat['utilization_pct']}% "
                            f"of limit ({count}/{COLLECTION_MAX_DOCS} docs)"
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ChromaDB monitor error: {e}")

    safe_create_task(_monitor_chroma())

    async def _archive_old_facts():
        """Background task: archive old facts for all users once per day."""
        from backend.memory.vector_store import get_all_collections_stats, VectorStore
        
        while True:
            try:
                await asyncio.sleep(86400)  # every 24 hours
                stats = await get_all_collections_stats()
                total_archived = 0
                
                for col_stat in stats.get("collections", []):
                    user_id = col_stat["user_id"]
                    vs = VectorStore(user_id=user_id)
                    archived = await vs.archive_old_facts()
                    total_archived += archived
                
                if total_archived > 0:
                    logger.info(f"Daily TTL archive: removed {total_archived} old facts")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TTL archiving task error: {e}")

    safe_create_task(_archive_old_facts())

    # Start COSMO Artist (Next.js template server)
    try:
        from backend.cosmo.artist import start_artist, stop_artist as stop_artist_fn
        artist_task = safe_create_task(start_artist())
        logger.info("COSMO Artist server starting on port 3005...")
    except ImportError:
        logger.warning("COSMO Artist not found. Skipping.")
    
    logger.info(f"Auth: {'ENABLED' if settings.AUTH_ENABLED else 'DISABLED (dev mode)'}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Playwright binary check (with timeout to prevent startup hang)
    try:
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "playwright", "help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode != 0:
            logger.warning("Playwright may not be installed. Presentation rendering limits will apply.")
    except asyncio.TimeoutError:
        logger.warning("Playwright check timed out (5s). Skipping.")
        try:
            process.kill()
        except Exception:
            pass
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
    try:
        from backend.cosmo.engine import stop_engine
        await stop_engine()
    except ImportError:
        pass
    try:
        from backend.cosmo.artist import stop_artist as stop_artist_fn
        await stop_artist_fn()
    except ImportError:
        pass

app = FastAPI(
    title="Archimedes COSMO",
    description="AI-powered full-stack development agent with specialized MCTS reasoning.",
    version="0.2.0",
    lifespan=lifespan
)

init_telemetry(app)

# Prometheus Middleware
@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status = response.status_code
    
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    
    return response

@app.get("/metrics")
async def metrics(request: Request):
    token = os.environ.get("METRICS_BEARER_TOKEN", "")
    is_dev = os.environ.get("ENVIRONMENT", "production").lower() == "development"
    
    if not is_dev:
        # In production: always require token
        from fastapi import Response
        if not token:
            return Response(status_code=403, content="METRICS_BEARER_TOKEN not configured")
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {token}":
            return Response(status_code=401)
    elif token:
        # In dev: only check if token is set
        from fastapi import Response
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {token}":
            return Response(status_code=401)
    
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
    if os.environ.get("ENVIRONMENT", "production").lower() == "development"
    else ""
).split(",")
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o.strip()]

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

from backend.api.council_router import router as council_router
app.include_router(council_router)



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
    except (ConnectionRefusedError, OSError) as e:
        logger.warning(f"Health check: database connection refused: {e}")
    except ImportError as e:
        logger.warning(f"Health check: database module not available: {e}")
    except Exception as e:
        logger.warning(f"Health check: database query failed ({type(e).__name__}): {e}")

    # Check Ollama
    ollama_ok = False
    try:
        import ollama
        client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        await client.list()
        ollama_ok = True
    except (ConnectionRefusedError, OSError, TimeoutError) as e:
        logger.warning(f"Health check: Ollama unreachable at {settings.OLLAMA_BASE_URL}: {e}")
    except ImportError:
        logger.warning("Health check: ollama package not installed")
    except Exception as e:
        logger.warning(f"Health check: Ollama check failed ({type(e).__name__}): {e}")

    # Check Memory Bank
    memory_ok = False
    try:
        from backend.memory.memory_bank import get_relevant_facts
        facts = await get_relevant_facts(limit=1)
        memory_ok = True
    except ImportError as e:
        logger.warning(f"Health check: memory_bank module unavailable: {e}")
    except Exception as e:
        logger.warning(f"Health check: memory bank failed ({type(e).__name__}): {e}")

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

@app.get("/api/health/models")
async def model_health():
    from backend.models.model_router import get_model_router
    router = get_model_router()
    return await router.get_health_status()

@app.get("/api/metrics/kv-cache")
async def kv_cache_stats():
    from backend.agent.monitoring.kv_cache_monitor import kv_cache_monitor
    return kv_cache_monitor.get_stats()

@app.get("/api/metrics/economy")
async def economy_stats():
    from backend.agent.economy.agent_economy import agent_economy
    return agent_economy.get_global_stats()

@app.get("/api/audit/{task_id}")
async def get_audit_trail(task_id: str, format: str = "json"):
    from backend.agent.transparency.audit_trail import audit_manager
    trail_data = audit_manager.get_completed(task_id)
    if not trail_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit trail not found")
    
    if format == "markdown":
        # Reconstruct markdown from stored data
        from fastapi import Response
        return Response(
            content=f"# Audit Trail\n\nTask: {trail_data['task']}\n\nEvents: {trail_data['event_count']}",
            media_type="text/markdown"
        )
    return trail_data

@app.get("/api/audit")
async def list_audit_trails():
    from backend.agent.transparency.audit_trail import audit_manager
    trails = audit_manager.get_all_completed()
    return {
        "count": len(trails),
        "trails": [
            {
                "task_id": t["task_id"],
                "task": t["task"][:60],
                "duration": t["total_duration_seconds"],
                "events": t["event_count"],
            }
            for t in trails[-10:]  # Last 10
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=reload)