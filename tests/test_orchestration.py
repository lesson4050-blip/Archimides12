import pytest
import asyncio
from backend.agent.orchestration.orchestrator import AgentOrchestrator
from backend.agent.orchestration.state import AgentMode
from backend.agent.tool_registry import ToolRegistry
from backend.memory.context_manager import ContextManager

class MockModelRouter:
    async def generate(self, messages, **kwargs):
        # Distinguish by role/instructions in last system message
        system_msgs = [m for m in messages if m.get("role") == "system"]
        last_system = system_msgs[-1].get("content", "") if system_msgs else ""
        
        if "Planner Agent" in last_system:
            return {"text": '{"strategy": "sequential", "phases": [{"title": "Test", "subtasks": [{"type": "execute", "description": "Do something"}]}]}'}
        elif "Executor Agent" in last_system:
            # If we've already seen a tool result for 'message', return a final confirmation
            if any(m.get("role") == "tool" and m.get("name") == "message" for m in messages):
                return {"text": "Final Result"}
            return {"text": "Executing...", "tool_call": {"name": "message", "params": {"type": "result", "content": "Final Result"}}}
        elif "Critic" in last_system or "AGENT ATTEMPT" in last_system:
            return {"text": "VERDICT: PASS"}
        return {"text": "Generic response"}

@pytest.mark.asyncio
async def test_orchestrator_planning_mode():
    """Verify the full Planner -> Executor -> Critic lifecycle."""
    router = MockModelRouter()
    registry = ToolRegistry()
    async def dummy_message(**kwargs):
        return {"success": True}
    registry.register("message", dummy_message)
    
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
    async def dummy_message(**kwargs):
        return {"success": True}
    registry.register("message", dummy_message)
    
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
