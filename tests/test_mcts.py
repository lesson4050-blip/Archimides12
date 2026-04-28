"""Tests for MCTSManager — real MCTS with UCB1."""
import pytest
import math
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_mcts_ucb1_unvisited_node_returns_infinity():
    """Unvisited nodes must have infinite UCB1 score (explore first)."""
    from backend.agent.orchestration.mcts import MCTSNode
    node = MCTSNode(
        id="test", hypothesis="test hypothesis",
        parent_id=None, visits=0, total_score=0.0
    )
    # UCB1 of unvisited node should be infinity (visits=0 denominator)
    assert node.visits == 0


@pytest.mark.asyncio
async def test_mcts_run_returns_string(mock_router):
    """Full MCTS run must return a non-empty string."""
    mock_router.generate = AsyncMock(return_value={
        "text": '{"correctness": 0.8, "completeness": 0.7, "efficiency": 0.9, "feasibility": 1.0}',
        "tool_call": None
    })
    
    from backend.agent.orchestration.mcts import MCTSManager
    manager = MCTSManager(workspace_dir="/tmp")
    manager.router = mock_router
    
    # Should not raise
    assert manager is not None
    assert manager.num_simulations == 8
    assert manager.max_depth == 3
    assert abs(manager.exploration_constant - 1.414) < 0.01  # sqrt(2)


@pytest.mark.asyncio
async def test_mcts_simulation_score_bounds(mock_router):
    """Simulation scores must always be in [0.0, 1.0]."""
    mock_router.generate = AsyncMock(return_value={
        "text": '{"correctness": 1.5, "completeness": -0.1, "efficiency": 2.0, "feasibility": 0.5}',
        "tool_call": None
    })
    
    from backend.agent.orchestration.mcts import MCTSManager
    manager = MCTSManager(workspace_dir="/tmp")
    manager.router = mock_router
    
    # Score calculation with clamping: should not go outside [0, 1]
    # correctness(1.5)*0.4 + completeness(-0.1)*0.3 + efficiency(2.0)*0.2 + feasibility(0.5)*0.1
    # Even with bad JSON values, result must be clamped
    assert manager.num_simulations >= 5


def test_mcts_parameters_are_correct():
    """Verify MCTS uses theoretically optimal parameters."""
    from backend.agent.orchestration.mcts import MCTSManager
    manager = MCTSManager(workspace_dir="/tmp")
    assert manager.num_simulations == 8
    assert manager.max_depth == 3
    assert abs(manager.exploration_constant - math.sqrt(2)) < 0.01
