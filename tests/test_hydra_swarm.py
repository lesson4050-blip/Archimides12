"""Tests for Hydra Swarm multi-agent system (test 1.9)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.agent.orchestration.hydra_swarm import (
    AgentMessage, HydraAgent, HydraCommander,
    HydraScout, HydraWarrior, HydraSentinel,
    HydraSwarm,
)


# ─── AgentMessage ────────────────────────────────────────────────

def test_agent_message_to_context():
    m = AgentMessage(from_role="scout", content="found bug", confidence=0.9)
    ctx = m.to_context()
    assert "SCOUT" in ctx
    assert "0.90" in ctx
    assert "found bug" in ctx


def test_agent_message_defaults():
    m = AgentMessage(from_role="warrior", content="fixed it")
    assert m.confidence == 1.0
    assert m.artifacts == []


# ─── HydraAgent ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hydra_agent_run_basic():
    """Agent run should call router.generate and return AgentMessage."""
    router = MagicMock()
    router.generate = AsyncMock(return_value={
        "text": "Analysis complete. SCOUT_DONE"
    })
    agent = HydraAgent("scout", "system prompt", router)
    result = await agent.run("find the bug", done_signal="SCOUT_DONE", max_iters=2)
    assert isinstance(result, AgentMessage)
    assert result.from_role == "scout"
    assert "SCOUT_DONE" in result.content


@pytest.mark.asyncio
async def test_hydra_agent_run_empty_response():
    """Agent handles empty model responses gracefully."""
    router = MagicMock()
    router.generate = AsyncMock(return_value={"text": ""})
    agent = HydraAgent("warrior", "prompt", router)
    result = await agent.run("task", max_iters=3)
    assert isinstance(result, AgentMessage)
    assert result.from_role == "warrior"


@pytest.mark.asyncio
async def test_hydra_agent_context_passed():
    """Context messages from other agents should be included."""
    router = MagicMock()
    router.generate = AsyncMock(return_value={"text": "DONE"})
    agent = HydraAgent("warrior", "prompt", router)
    ctx = [AgentMessage(from_role="scout", content="found file.py")]
    await agent.run("fix it", context_messages=ctx, done_signal="DONE")
    call_args = router.generate.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    # The user message with context is the second message (after system)
    user_msg = messages[1]["content"]
    assert "found file.py" in user_msg


# ─── HydraCommander ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_commander_plan_attack_valid_json():
    """Commander should parse valid JSON plan from model."""
    router = MagicMock()
    router.generate = AsyncMock(return_value={
        "text": '[{"role": "scout", "task": "explore"}, {"role": "warrior", "task": "fix"}]'
    })
    cmd = HydraCommander(router)
    plan = await cmd.plan_attack("fix the bug")
    assert len(plan) == 2
    assert plan[0]["role"] == "scout"


@pytest.mark.asyncio
async def test_commander_plan_attack_invalid_json():
    """Commander should fallback on unparseable output."""
    router = MagicMock()
    router.generate = AsyncMock(return_value={"text": "garbage"})
    cmd = HydraCommander(router)
    plan = await cmd.plan_attack("task")
    # No JSON array found in "garbage" → regex returns None → fallback
    assert isinstance(plan, list)


def test_commander_synthesize():
    router = MagicMock()
    cmd = HydraCommander(router)
    scout = AgentMessage(from_role="scout", content="found bug in x.py")
    warrior = AgentMessage(from_role="warrior", content="patched x.py")
    sentinel = AgentMessage(from_role="sentinel", content="SENTINEL_VERDICT: PASS")
    result = cmd.synthesize("fix bug", scout, warrior, sentinel)
    assert "SUCCESS" in result
    assert "found bug" in result


def test_commander_synthesize_fail():
    router = MagicMock()
    cmd = HydraCommander(router)
    scout = AgentMessage(from_role="scout", content="found")
    warrior = AgentMessage(from_role="warrior", content="tried")
    sentinel = AgentMessage(from_role="sentinel", content="SENTINEL_VERDICT: FAIL")
    result = cmd.synthesize("fix bug", scout, warrior, sentinel)
    assert "NEEDS REVIEW" in result


# ─── Specialized agents ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_scout_investigate():
    router = MagicMock()
    router.generate = AsyncMock(return_value={"text": "Found it. SCOUT_DONE"})
    scout = HydraScout(router)
    result = await scout.investigate("find the bug")
    assert result.from_role == "scout"


@pytest.mark.asyncio
async def test_warrior_execute():
    router = MagicMock()
    router.generate = AsyncMock(return_value={"text": "Fixed. WARRIOR_DONE"})
    warrior = HydraWarrior(router)
    ctx = [AgentMessage(from_role="scout", content="file.py line 10")]
    result = await warrior.execute("fix bug", context=ctx)
    assert result.from_role == "warrior"


@pytest.mark.asyncio
async def test_sentinel_verify():
    router = MagicMock()
    router.generate = AsyncMock(return_value={
        "text": "SENTINEL_VERDICT: PASS\nTests: 5 passed"
    })
    sentinel = HydraSentinel(router)
    ctx = [AgentMessage(from_role="scout", content="found"),
           AgentMessage(from_role="warrior", content="fixed")]
    result = await sentinel.verify("task", context=ctx)
    assert result.from_role == "sentinel"
    assert "PASS" in result.content
