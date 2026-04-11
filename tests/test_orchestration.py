import pytest
import asyncio
from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.agent.orchestration.state import AgentMode
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

class MockModelRouter:
    async def generate(self, messages, **kwargs):
        content = str(messages[-1]["content"])
        if "Task:" in content:
            # Planner response
            return {"text": '{"strategy": "sequential", "phases": [{"title": "Test", "subtasks": [{"type": "execute", "description": "Do something"}]}]}'}
        elif "Do something" in content:
            # Executor response
            return {"text": "Step completed successfully", "tool_call": {"name": "message", "params": {"type": "result", "content": "Final Result"}}}
        elif "AGENT ATTEMPT" in content:
            # Critic response
            return {"text": "VERDICT: PASS"}
        return {"text": "Generic response"}

@pytest.mark.asyncio
async def test_orchestrator_planning_mode():
    """Verify the full Planner -> Executor -> Critic lifecycle."""
    router = MockModelRouter()
    registry = ToolRegistry()
    # Register dummy message tool
    registry.register("message", lambda **kwargs: {"success": True})
    
    cm = ContextManager(max_tokens=1000)
    orch = AgentOrchestrator(router, registry, cm)
    
    result = await orch.run_task(
        task_description="Test my flow",
        mode=AgentMode.PLANNING,
        session_id="test-session"
    )
    
    assert result["success"] is True
    assert result["output"] == "Final Result"
    assert result["mode"] == "planning"
    assert result["plan"] is not None

@pytest.mark.asyncio
async def test_orchestrator_fast_mode():
    """Verify the direct execution lifecycle (no planning)."""
    router = MockModelRouter()
    registry = ToolRegistry()
    registry.register("message", lambda **kwargs: {"success": True})
    
    cm = ContextManager(max_tokens=1000)
    orch = AgentOrchestrator(router, registry, cm)
    
    result = await orch.run_task(
        task_description="Do something fast",
        mode=AgentMode.FAST,
        session_id="test-session"
    )
    
    assert result["success"] is True
    assert result["mode"] == "fast"
    assert result["plan"] is None # Fast mode skips planner
