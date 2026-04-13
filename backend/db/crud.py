"""
Database CRUD operations with PostgreSQL + SQLite fallback.
Automatically detects available database and configures connection pooling.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from backend.db.models import Base, Session, Task, Message, Artifact, User
from backend.config import settings

logger = logging.getLogger(__name__)


def _create_engine():
    """Create async engine with PostgreSQL priority and SQLite fallback."""
    db_url = settings.DATABASE_URL
    
    if db_url.startswith("postgresql"):
        try:
            engine = create_async_engine(
                db_url,
                echo=False,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
            )
            logger.info(f"Database: PostgreSQL (pool_size={settings.DB_POOL_SIZE})")
            return engine
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable ({e}), falling back to SQLite")
    
    # Fallback to SQLite
    sqlite_url = settings.DATABASE_URL_SQLITE
    engine = create_async_engine(sqlite_url, echo=False)
    logger.info(f"Database: SQLite fallback ({sqlite_url})")
    return engine


engine = _create_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """Initialize database tables with robust fallback."""
    global engine, AsyncSessionLocal
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized.")
    except Exception as e:
        if settings.DATABASE_URL.startswith("postgresql"):
            logger.warning(f"PostgreSQL connection failed ({e}), falling back to SQLite")
            # Re-initialize engine and sessionmaker with SQLite
            engine = create_async_engine(settings.DATABASE_URL_SQLITE, echo=False)
            AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Database tables initialized using SQLite fallback ({settings.DATABASE_URL_SQLITE}).")
        else:
            logger.error(f"Critical database initialization error: {e}")
            raise

    # Auto-create dev-user if AUTH_ENABLED is False (dev bypass mode)
    if not settings.AUTH_ENABLED:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == "dev-user"))
            if not result.scalar_one_or_none():
                dev_user = User(
                    id="dev-user",
                    email="dev@cosmo.ai",
                    hashed_password="builtin_bypass", # Not checked in bypass mode
                    role="admin"
                )
                db.add(dev_user)
                await db.commit()
                logger.info("Created default 'dev-user' for development.")


async def create_session(session_id: str):
    async with AsyncSessionLocal() as db:
        # Check if session already exists
        existing = await db.execute(select(Session).where(Session.id == session_id))
        if existing.scalar_one_or_none():
            return None
        new_session = Session(id=session_id)
        db.add(new_session)
        await db.commit()
        return new_session


async def get_session(session_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()


async def create_task(session_id: str, goal: str):
    async with AsyncSessionLocal() as db:
        new_task = Task(session_id=session_id, goal=goal, status="pending")
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        return new_task


async def update_task_plan(task_id: int, plan: list):
    async with AsyncSessionLocal() as db:
        await db.execute(update(Task).where(Task.id == task_id).values(plan=plan))
        await db.commit()


async def add_message(session_id: str, role: str, content: str, metadata: dict = None):
    async with AsyncSessionLocal() as db:
        new_msg = Message(session_id=session_id, role=role, content=content, metadata_json=metadata)
        db.add(new_msg)
        await db.commit()
        return new_msg


async def get_session_messages(session_id: str, limit: int = 100):
    """Retrieve message history for a session."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
