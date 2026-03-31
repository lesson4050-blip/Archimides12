from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from backend.db.models import Base, Session, Task, Message, Artifact
from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def create_session(session_id: str):
    async with AsyncSessionLocal() as db:
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
