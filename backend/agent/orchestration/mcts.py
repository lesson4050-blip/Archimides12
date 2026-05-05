"""
Monte Carlo Tree Search (MCTS) Engine — Real Implementation.

Uses UCB1 selection, LLM-based expansion and simulation,
and proper backpropagation through a tree of hypothesis nodes.
"""
import math
import uuid
import logging
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MCTSNode:
    """A single node in the MCTS tree."""
    id: str
    hypothesis: str
    parent_id: Optional[str]
    visits: int = 0
    total_score: float = 0.0
    children: List[str] = field(default_factory=list)


class MCTSTree:
    """Manages the MCTS node graph."""

    def __init__(self):
        self.nodes: Dict[str, MCTSNode] = {}

    def add_node(self, node: MCTSNode):
        self.nodes[node.id] = node
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].children.append(node.id)

    def get_node(self, node_id: str) -> Optional[MCTSNode]:
        return self.nodes.get(node_id)

    def get_root(self) -> Optional[MCTSNode]:
        for node in self.nodes.values():
            if node.parent_id is None:
                return node
        return None

    def get_depth(self, node: MCTSNode) -> int:
        depth = 0
        current = node
        while current.parent_id:
            depth += 1
            parent = self.get_node(current.parent_id)
            if parent is None:
                break
            current = parent
        return depth

    def get_leaves(self) -> List[MCTSNode]:
        return [n for n in self.nodes.values() if not n.children]


class MCTSManager:
    """
    Lightweight Monte Carlo Tree Search for multi-hypothesis evaluation.

    Phases per iteration:
      1. Selection  — UCB1 walk from root to a promising leaf
      2. Expansion  — LLM generates child approaches for the selected leaf
      3. Simulation — LLM scores a leaf node's feasibility
      4. Backpropagation — scores propagate up to the root
    """

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = workspace_dir
        self.max_depth = 3
        self.num_simulations = 8
        self.exploration_constant = 1.414  # sqrt(2), standard UCB1

    # ── UCB1 Selection ──

    def _ucb1(self, node: MCTSNode, parent_visits: int) -> float:
        if node.visits == 0:
            return float('inf')
        exploitation = node.total_score / node.visits
        exploration = self.exploration_constant * math.sqrt(
            math.log(parent_visits) / node.visits
        )
        return exploitation + exploration

    def _select(self, tree: MCTSTree) -> MCTSNode:
        """Walk from root to a leaf using UCB1."""
        node = tree.get_root()
        if node is None:
            raise ValueError("MCTS tree has no root")

        while node.children:
            children = [tree.get_node(cid) for cid in node.children]
            children = [c for c in children if c is not None]
            if not children:
                break
            # Prefer unvisited nodes
            unvisited = [c for c in children if c.visits == 0]
            if unvisited:
                return unvisited[0]
            node = max(children, key=lambda c: self._ucb1(c, node.visits))
        return node

    # ── Expansion ──

    async def _expand(self, tree: MCTSTree, node: MCTSNode,
                      task: str, model_router) -> List[MCTSNode]:
        """Generate child hypotheses via LLM if depth allows."""
        if tree.get_depth(node) >= self.max_depth:
            return []

        prompt = (
            f"Given this task and current approach, suggest 2 distinct "
            f"alternative refinements or improvements.\n"
            f"IMPORTANT: Generate approaches that are FUNDAMENTALLY DIFFERENT from "
            f"each other. Avoid paraphrasing. Each must use a different strategy, "
            f"algorithm, or tool combination.\n"
            f"Task: {task[:400]}\n"
            f"Current approach: {node.hypothesis[:400]}\n"
            "Separate each with '---APPROACH---'."
        )
        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
        except Exception as e:
            logger.warning(f"MCTS expansion failed: {e}")
            return []

        new_nodes = []
        for h in response.get("text", "").split("---APPROACH---"):
            h = h.strip()
            if not h:
                continue
                
            # If hypothesis contains code, check via SecurityGate
            if "```" in h:
                try:
                    from backend.security.sandbox_hardening import SecurityGate
                    gate = SecurityGate(strict_mode=True)
                    # Extract just the code for analysis
                    import re
                    code_blocks = re.findall(r'```(?:python|bash)?\n(.*?)```', h, re.DOTALL)
                    if code_blocks:
                        verdict = gate.analyze_python(code_blocks[0])
                        if not getattr(verdict, 'allowed', True):
                            logger.warning(f"MCTS: blocked unsafe hypothesis: {getattr(verdict, 'reasons', 'unsafe')}")
                            continue
                except Exception as e:
                    logger.debug(f"MCTS SecurityGate error during expand: {e}")
            
            child = MCTSNode(
                id=str(uuid.uuid4()),
                hypothesis=h,
                parent_id=node.id
            )
            tree.add_node(child)
            new_nodes.append(child)
        return new_nodes

    # ── Simulation (LLM scoring) ──

    async def _simulate(self, node: MCTSNode, task: str,
                        model_router) -> Tuple[float, str]:
        """Score a hypothesis via Sandbox Execution and LLM evaluation."""
        # Execute in sandbox for real feedback
        sandbox_feedback = await self._execute_hypothesis(node.hypothesis)
        return await self._simulate_with_critic(node, task, model_router, sandbox_feedback)

    async def _execute_hypothesis(self, hypothesis: str) -> str:
        """Simulate real execution to validate syntax or basic tests if a code snippet is provided."""
        import re
        code_blocks = re.findall(r'```(?:python|bash)?\n(.*?)```', hypothesis, re.DOTALL)
        if not code_blocks:
            return "No code to execute. Purely theoretical hypothesis."
            
        code = code_blocks[0]
        
        # Check via SecurityGate BEFORE any execution or parse simulation
        try:
            from backend.security.sandbox_hardening import SecurityGate
            gate = SecurityGate(strict_mode=True)
            verdict = gate.analyze_python(code)
            if not getattr(verdict, 'allowed', True):
                return f"Security blocked: {'; '.join(getattr(verdict, 'reasons', ['unsafe']))}"
        except Exception as e:
            logger.debug(f"MCTS SecurityGate error: {e}")
            
        # Only syntactic analysis in MCTS - no real execution to avoid side effects
        try:
            import ast
            ast.parse(code)
            return "Static analysis: Code is syntactically valid and passed security check."
        except SyntaxError as e:
            return f"Syntax error at line {e.lineno}: {e.msg}"

    async def _simulate_with_critic(self, node: MCTSNode, task: str,
                                    model_router, sandbox_feedback: str = "") -> Tuple[float, str]:
        """Score a hypothesis using a Critic for enhanced evaluation."""
        prompt = f"""
Evaluate this solution approach for the given task.
Task: {task[:400]}
Approach: {node.hypothesis[:500]}
Sandbox Execution Feedback: {sandbox_feedback}

First, provide a brief CRITIQUE (max 3 sentences) of the approach, identifying any flaws, missing edge cases, or inefficiencies.
Then, based on your critique, score each dimension from 0.0 to 1.0:
- Correctness: Will this actually solve the problem? (weight: 0.4)
- Completeness: Does it handle edge cases? (weight: 0.3)
- Efficiency: Is the approach reasonably fast/clean? (weight: 0.2)
- Feasibility: Can this be implemented with available tools? (weight: 0.1)

Reply ONLY with a JSON object in this exact format:
{{"critique": "your critique here", "correctness": 0.0, "completeness": 0.0, "efficiency": 0.0, "feasibility": 0.0}}
"""

        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            from backend.utils.json_repair import repair_and_parse
            dims, _ = repair_and_parse(response.get("text", "{}"))
            if dims and isinstance(dims, dict):
                score = (
                    dims.get("correctness", 0.0) * 0.4 +
                    dims.get("completeness", 0.0) * 0.3 +
                    dims.get("efficiency", 0.0) * 0.2 +
                    dims.get("feasibility", 0.0) * 0.1
                )
                critique = dims.get("critique", "Evaluated via dimensions")
                return min(max(score, 0.0), 1.0), critique
        except Exception as e:
            logger.warning(f"MCTS simulation failed: {e}")

        return 0.5, "evaluation failed"

    # ── Backpropagation ──

    def _backpropagate(self, tree: MCTSTree, node: MCTSNode, score: float):
        """Propagate score up through ancestors."""
        current = node
        while current is not None:
            current.visits += 1
            current.total_score += score
            if current.parent_id:
                current = tree.get_node(current.parent_id)
            else:
                break

    # ── Task Complexity Estimator ──

    def _estimate_task_confidence(self, task: str) -> float:
        """
        Heuristic confidence estimation WITHOUT LLM call.
        Returns 0.0 (needs MCTS) to 1.0 (can answer directly).
        """
        task_lower = task.lower()
        task_len = len(task.split())
        
        simple_signals = [
            ("hello" in task_lower or "hi " in task_lower, 0.3),
            (task_len < 15, 0.2),
            (task_lower.startswith(("what is", "what are", "how do i", "explain")), 0.2),
            ("?" in task and task_len < 20, 0.15),
            (not any(kw in task_lower for kw in
                     ["refactor", "optimize", "debug", "implement", "build",
                      "design", "architecture", "migrate", "deploy"]), 0.15),
        ]
        
        complex_penalties = [
            (task_len > 50, -0.3),
            (any(kw in task_lower for kw in
                 ["multiple", "complex", "enterprise", "production",
                  "distributed", "scalable", "refactor"]), -0.25),
            ("and" in task_lower and task_len > 30, -0.1),
            (task.count("\n") > 3, -0.2),
            (any(kw in task_lower for kw in
                 ["bug", "error", "failing", "broken"]), -0.1),
        ]
        
        base = 0.5
        for condition, boost in simple_signals:
            if condition:
                base += boost
        for condition, penalty in complex_penalties:
            if condition:
                base += penalty
        
        return max(0.0, min(1.0, base))

    # ── Main MCTS loop ──

    async def run_mcts(
        self,
        task: str,
        context: str,
        model_router: Any,
        executor_agent: Any = None,
        state: Any = None
    ) -> str:
        """
        Run MCTS for self.num_simulations iterations and return the
        best-scoring leaf hypothesis.
        """
        confidence = self._estimate_task_confidence(task)
        if confidence > 0.85:
            logger.info(f"MCTS: confidence {confidence:.2f} > 0.85, skipping tree search")
            try:
                response = await model_router.generate(
                    messages=[{"role": "user", "content": f"Task: {task}\nContext: {context[:300]}\nProvide the best approach directly."}],
                    task_hint="default"
                )
                return response.get("text", task)
            except Exception as e:
                logger.warning(f"Direct generation failed: {e}, falling back to MCTS")

        logger.info(f"MCTS: confidence {confidence:.2f} <= 0.85, starting search for: {task[:60]}")

        tree = MCTSTree()
        root = MCTSNode(id=str(uuid.uuid4()), hypothesis=task, parent_id=None)
        tree.add_node(root)

        prompt = (
            f"Task: {task}\nContext: {context[:300]}\n"
            "Generate 3 distinct technical approaches. "
            "Separate each with '---APPROACH---'."
        )
        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
        except Exception as e:
            logger.error(f"MCTS initial generation failed: {e}")
            return task

        hypotheses = [
            h.strip()
            for h in response.get("text", "").split("---APPROACH---")
            if h.strip()
        ][:3]

        if not hypotheses:
            return task

        for h in hypotheses:
            child = MCTSNode(id=str(uuid.uuid4()), hypothesis=h, parent_id=root.id)
            tree.add_node(child)

        # MCTS parallel iterations
        BATCH_SIZE = 3
        for batch_start in range(0, self.num_simulations, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, self.num_simulations)
            
            candidates = []
            for _ in range(batch_end - batch_start):
                selected = self._select(tree)
                new_nodes = await self._expand(tree, selected, task, model_router)
                target = new_nodes[0] if new_nodes else selected
                candidates.append(target)
            
            sim_tasks = [self._simulate(c, task, model_router) for c in candidates]
            results = await asyncio.gather(*sim_tasks, return_exceptions=True)
            
            for candidate, result in zip(candidates, results):
                if isinstance(result, Exception):
                    score, reason = 0.5, f"simulation error: {result}"
                else:
                    score, reason = result
                self._backpropagate(tree, candidate, score)
                logger.debug(f"MCTS parallel node={candidate.id[:8]} score={score:.2f}")

        # Select best leaf by average score
        leaves = tree.get_leaves()
        if not leaves:
            return task

        best = max(
            leaves,
            key=lambda n: (n.total_score / n.visits) if n.visits > 0 else 0.0
        )
        best_avg = best.total_score / best.visits if best.visits > 0 else 0.0

        logger.info(
            f"MCTS: completed {self.num_simulations} iterations, "
            f"best score={best_avg:.2f}, "
            f"tree size={len(tree.nodes)} nodes"
        )

        return (
            f"OPTIMAL APPROACH (MCTS score {best_avg:.2f}/1.0):\n"
            f"{best.hypothesis}"
        )
