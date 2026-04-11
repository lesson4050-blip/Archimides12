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


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Archimedes Backend starting up...")
    await init_db()

    # Clean up stale containers from previous runs
    sandbox_manager.cleanup_stale_containers()

    # Start the inactivity reaper
    sandbox_manager.start_reaper()
    
    logger.info(f"Auth: {'ENABLED' if settings.AUTH_ENABLED else 'DISABLED (dev mode)'}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    yield

    # Shutdown
    logger.info("Archimedes Backend shutting down... Cleaning up sandboxes.")
    sandbox_manager.stop_reaper()
    sandbox_manager.cleanup()

app = FastAPI(
    title="Archimedes API",
    description="Backend for the Archimedes Autonomous AI Agent",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(main_router)



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
