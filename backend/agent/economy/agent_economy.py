"""
Internal Agent Economy.

Agents have computational "credit" costs based on their complexity.
The orchestrator allocates a budget per task.
Agents bid on subtasks — cheapest capable agent wins.
Expensive agents (architect) are only hired for complex tasks.

This implements real resource optimization, not just metaphor.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AgentTier(str, Enum):
    NANO = "nano"      # 1 credit — simple, fast (fact_checker, formatter)
    MICRO = "micro"    # 3 credits — standard (coder, researcher)
    MACRO = "macro"    # 8 credits — heavy (architect, optimizer)
    MEGA = "mega"      # 20 credits — maximum (multi-model consensus)


# Cost per agent role in credits
AGENT_COSTS: Dict[str, int] = {
    "fact_checker": 1,
    "formatter": 1,
    "coder": 3,
    "researcher": 3,
    "tester": 3,
    "critic": 5,
    "optimizer": 8,
    "architect": 8,
    "consensus": 20,
}

# What each agent can do (capabilities)
AGENT_CAPABILITIES: Dict[str, List[str]] = {
    "fact_checker": ["verify", "check", "validate"],
    "coder": ["code", "implement", "write", "fix", "debug"],
    "researcher": ["research", "find", "search", "analyze", "compare"],
    "tester": ["test", "verify", "qa", "coverage"],
    "critic": ["review", "audit", "security", "quality"],
    "architect": ["design", "architecture", "system", "plan", "structure"],
    "optimizer": ["optimize", "performance", "refactor", "speed"],
    "consensus": ["decide", "arbitrate", "synthesize"],
}


@dataclass
class AgentBid:
    role: str
    cost: int
    confidence: float  # 0.0 to 1.0 — how confident this agent can do the task
    estimated_steps: int  # estimated tool calls needed


@dataclass
class EconomyTransaction:
    timestamp: float
    task_id: str
    agent_role: str
    credits_spent: int
    success: bool
    duration_seconds: float


@dataclass
class TaskBudget:
    task_id: str
    total_credits: int
    spent_credits: int = 0
    transactions: List[EconomyTransaction] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return self.total_credits - self.spent_credits

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

    def spend(self, role: str, cost: int, success: bool, duration: float):
        self.spent_credits += cost
        self.transactions.append(EconomyTransaction(
            timestamp=time.time(),
            task_id=self.task_id,
            agent_role=role,
            credits_spent=cost,
            success=success,
            duration_seconds=duration
        ))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "total_credits": self.total_credits,
            "spent_credits": self.spent_credits,
            "remaining_credits": self.remaining,
            "efficiency": round(
                sum(1 for t in self.transactions if t.success) /
                len(self.transactions) if self.transactions else 1.0, 2
            ),
            "transactions": [
                {
                    "agent": t.agent_role,
                    "credits": t.credits_spent,
                    "success": t.success,
                    "duration": round(t.duration_seconds, 2)
                }
                for t in self.transactions
            ]
        }


class AgentEconomy:
    """
    Manages agent hiring, budgets, and bidding.
    
    The economy optimizes for:
    1. Task completion (primary)
    2. Minimum credit spend (secondary)
    3. Best agent for the job (tertiary)
    """

    # Default budget per task complexity
    BUDGET_BY_COMPLEXITY = {
        "simple": 10,    # quick Q&A, facts
        "standard": 30,  # coding, research
        "complex": 60,   # architecture, multi-step
        "unlimited": 200 # critical tasks
    }

    def __init__(self):
        self._active_budgets: Dict[str, TaskBudget] = {}
        self._global_stats = {
            "total_tasks": 0,
            "total_credits_spent": 0,
            "total_credits_saved": 0,  # vs always using max agents
        }

    def allocate_budget(self, task_id: str, complexity: str = "standard") -> TaskBudget:
        """Allocate credit budget for a task."""
        credits = self.BUDGET_BY_COMPLEXITY.get(complexity, 30)
        budget = TaskBudget(task_id=task_id, total_credits=credits)
        self._active_budgets[task_id] = budget
        logger.info(f"[Economy] Task {task_id}: allocated {credits} credits ({complexity})")
        return budget

    def bid_for_task(self, subtask: str, available_budget: int) -> List[AgentBid]:
        """
        Generate bids from all agents for a subtask.
        Returns sorted list of bids (best value first).
        """
        subtask_lower = subtask.lower()
        bids = []

        for role, capabilities in AGENT_CAPABILITIES.items():
            cost = AGENT_COSTS.get(role, 3)

            # Skip if too expensive
            if cost > available_budget:
                continue

            # Calculate confidence based on keyword match
            matched = sum(
                1 for cap in capabilities
                if cap in subtask_lower
            )
            confidence = min(1.0, matched * 0.4 + 0.2)

            if confidence > 0.1:  # Only bid if somewhat relevant
                bids.append(AgentBid(
                    role=role,
                    cost=cost,
                    confidence=confidence,
                    estimated_steps=max(2, matched * 3)
                ))

        # Sort by value score (confidence / cost)
        bids.sort(key=lambda b: b.confidence / (b.cost + 0.1), reverse=True)
        return bids[:3]  # Top 3 bidders

    def select_agent(
        self,
        subtask: str,
        available_budget: int,
        require_capability: Optional[str] = None
    ) -> Optional[str]:
        """
        Select the best agent for a subtask within budget.
        Returns agent role name or None if no agent can do it.
        """
        bids = self.bid_for_task(subtask, available_budget)

        if require_capability:
            # Filter to agents that have the required capability
            bids = [
                b for b in bids
                if require_capability in AGENT_CAPABILITIES.get(b.role, [])
            ]

        if not bids:
            logger.warning(f"[Economy] No agent can handle: '{subtask[:50]}' (budget: {available_budget})")
            return None

        winner = bids[0]
        logger.info(
            f"[Economy] Hired {winner.role} for '{subtask[:40]}' "
            f"(cost: {winner.cost}, confidence: {winner.confidence:.1%})"
        )
        return winner.role

    def record_completion(
        self,
        task_id: str,
        agent_role: str,
        success: bool,
        duration: float
    ):
        """Record agent task completion and deduct credits."""
        budget = self._active_budgets.get(task_id)
        if not budget:
            return

        cost = AGENT_COSTS.get(agent_role, 3)
        budget.spend(agent_role, cost, success, duration)

        self._global_stats["total_credits_spent"] += cost
        if not success:
            logger.warning(f"[Economy] {agent_role} failed — {cost} credits lost")

    def get_budget_report(self, task_id: str) -> Optional[dict]:
        """Get spending report for a task."""
        budget = self._active_budgets.get(task_id)
        return budget.to_dict() if budget else None

    def close_task(self, task_id: str) -> Optional[dict]:
        """Close task budget and return final report."""
        budget = self._active_budgets.pop(task_id, None)
        if budget:
            self._global_stats["total_tasks"] += 1
            report = budget.to_dict()
            logger.info(
                f"[Economy] Task {task_id} closed: "
                f"{budget.spent_credits}/{budget.total_credits} credits used"
            )
            return report
        return None

    def get_global_stats(self) -> dict:
        return {
            **self._global_stats,
            "active_tasks": len(self._active_budgets),
        }


# Global singleton
agent_economy = AgentEconomy()
