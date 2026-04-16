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
from backend.api.presentation_router import router as presentation_router


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Archimedes Backend starting up...")
    
    if not settings.JWT_SECRET_KEY:
        import secrets
        settings.JWT_SECRET_KEY = secrets.token_hex(32)
        logger.warning("IMPORTANT: JWT_SECRET_KEY is not set in .env! Generated new key.")
        try:
            with open(".env", "a") as f:
                f.write(f"\nJWT_SECRET_KEY={settings.JWT_SECRET_KEY}\n")
            logger.info("Saved new JWT_SECRET_KEY to .env file to prevent session loss on restart.")
        except Exception as e:
            logger.error(f"Failed to append JWT key to .env: {e}. Existing tokens will be invalidated on server restart.")
    
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
    asyncio.create_task(_preload_model())

    # Start the inactivity reaper
    sandbox_manager.start_reaper()
    
    # Start the scheduler
    from backend.tools.scheduler_singleton import get_scheduler
    get_scheduler().start()
    
    logger.info(f"Auth: {'ENABLED' if settings.AUTH_ENABLED else 'DISABLED (dev mode)'}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Playwright binary check
    import subprocess
    try:
        result = subprocess.run(["python", "-m", "playwright", "help"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Playwright may not be installed. Presentation rendering limits will apply.")
    except Exception:
        logger.warning("Playwright check failed. Run `pip install playwright` and `playwright install` to enable PDF generation.")

    yield

    # Shutdown
    logger.info("Archimedes Backend shutting down... Cleaning up sandboxes.")
    sandbox_manager.stop_reaper()
    await sandbox_manager.cleanup()

app = FastAPI(
    title="Archimedes API",
    description="Backend for the Archimedes Autonomous AI Agent",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(main_router)
app.include_router(settings_router)
app.include_router(presentation_router, prefix="/api/v1")



@app.get("/")
async def root():
    return {"message": "Archimedes API is running."}


@app.get("/api/health")
async def api_health():
    """Top-level health check (без prefix /api/v1)."""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "2.0.0-cosmo"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
