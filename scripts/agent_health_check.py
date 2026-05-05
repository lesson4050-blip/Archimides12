import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.models.model_router import get_model_router
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

async def test_agent_sanity():
    print("--- Starting Agent Health Check (No Emoji Edition) ---")
    
    # Initialize components
    router = get_model_router()
    registry = ToolRegistry()
    context = ContextManager()
    
    orchestrator = AgentOrchestrator(router, registry, context)
    
    test_cases = [
        "привет",
        "Hello, how are you today?",
        "Hola, que tal?",
        "Как тебя зовут?",
        "Напиши функцию на python которая считает фибоначчи"
    ]
    
    results = []
    
    for i, task in enumerate(test_cases):
        print(f"\n[Test {i+1}] Input: '{task}'")
        start_time = time.time()
        try:
            result = await orchestrator.run_task(task, session_id=f"health_check_{i}")
            duration = time.time() - start_time
            output = result.get("output", "")
            success = result.get("success", False)
            strategy = result.get("strategy", "unknown")
            
            status = "PASSED" if success and output else "FAILED"
            print(f"Status: {status}")
            print(f"Latency: {duration:.2f}s")
            print(f"Strategy: {strategy}")
            print(f"Response: {output[:100]}...")
            
            results.append({
                "task": task,
                "status": status,
                "latency": duration,
                "strategy": strategy
            })
        except Exception as e:
            print(f"CRASHED: {e}")
            results.append({"task": task, "status": "CRASHED", "error": str(e)})

    print("\n--- Final Summary ---")
    for r in results:
        print(f"Task: {r['task'][:20]:<20} | Status: {r['status']:<8} | Latency: {r.get('latency', 0):.2f}s | Strategy: {r.get('strategy', 'N/A')}")

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    asyncio.run(test_agent_sanity())
