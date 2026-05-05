import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.models.model_router import get_model_router
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager
from backend.sandbox.manager import SandboxManager
from backend.db.crud import init_db, get_session_messages, get_session
from sqlalchemy import select
from backend.db.crud import AsyncSessionLocal
from backend.db.models import Message, Task

async def run_e2e_verification():
    print("--- Starting Archimedes E2E Verification ---")
    
    # 1. Initialize DB
    await init_db()
    
    # 2. Initialize Components
    router = get_model_router()
    sandbox = SandboxManager()
    registry = ToolRegistry() # Registry uses SandboxManager internally
    context = ContextManager()
    
    orchestrator = AgentOrchestrator(router, registry, context)
    
    session_id = f"e2e_test_{int(asyncio.get_event_loop().time())}"
    task = "Create a file named 'verify_db.txt' and write 'DB_CHECK_PASSED' inside it."
    
    print(f"Session ID: {session_id}")
    print(f"Task: {task}")
    
    try:
        # 3. Run Task
        result = await orchestrator.run_task(task, session_id=session_id)
        print(f"Agent Output: {result.get('output', 'NO OUTPUT')}")
        
        # 4. Verify Database Records
        print("\n[DB CHECK]")
        async with AsyncSessionLocal() as db:
            # Check for messages
            messages = await get_session_messages(session_id)
            print(f"Found {len(messages)} messages in DB for this session.")
            for msg in messages:
                print(f"  - [{msg.role}]: {msg.content[:50]}...")
            
            # Check for tasks
            from backend.db.models import Task
            stmt = select(Task).where(Task.session_id == session_id)
            tasks = (await db.execute(stmt)).scalars().all()
            print(f"Found {len(tasks)} task records in DB.")

        # 5. Verify Sandbox Filesystem
        print("\n[SANDBOX CHECK]")
        fs = sandbox.filesystem
        read_res = await fs.read_file(session_id, "verify_db.txt")
        if read_res.get("success"):
            print(f"File found in sandbox! Content: {read_res.get('content').strip()}")
        else:
            print(f"File NOT found in sandbox: {read_res.get('error')}")

    except Exception as e:
        print(f"E2E Verification CRASHED: {e}")
    finally:
        # Cleanup
        await sandbox.destroy_session(session_id)
        print("\n--- Verification Finished ---")

if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
