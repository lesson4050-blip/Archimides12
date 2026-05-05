"""
MemoryRouter — unified interface for all memory subsystems.

Three-tier memory model:
  Working memory  → context_manager (current session, in-context)
  Episodic memory → session_memory + vector_store (past sessions, searchable)
  Semantic memory → knowledge_graph (entities, relationships, facts)

Usage:
  router = MemoryRouter(user_id, session_id)
  context = await router.get_relevant_context(task, max_tokens=2000)
  await router.store(task, result, memory_type="episodic")
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    working: str = ""       # Current session context (always included)
    episodic: str = ""      # Relevant past episodes
    semantic: str = ""      # Relevant facts/entities from knowledge graph
    total_tokens_est: int = 0


class MemoryRouter:
    def __init__(self, user_id: str = "default", session_id: str = "default"):
        self.user_id = user_id
        self.session_id = session_id
        self._context_mgr = None
        self._vector_store = None
        self._knowledge_graph = None
        self._session_memory = None

    async def _init_lazy(self):
        """Lazy initialization — don't import heavy modules at startup."""
        if self._context_mgr is None:
            try:
                from backend.memory.context_manager import ContextManager
                self._context_mgr = ContextManager()
            except Exception as e:
                logger.warning(f"ContextManager init failed: {e}")
        
        if self._vector_store is None:
            try:
                from backend.memory.vector_store import VectorStore
                self._vector_store = VectorStore(user_id=self.user_id)
            except Exception as e:
                logger.warning(f"VectorStore init failed: {e}")
        
        if self._knowledge_graph is None:
            try:
                from backend.memory.knowledge_graph import KnowledgeGraph
                self._knowledge_graph = KnowledgeGraph()
            except Exception as e:
                logger.warning(f"KnowledgeGraph init failed: {e}")

    async def get_relevant_context(
        self,
        task: str,
        max_tokens: int = 2000,
        include_episodic: bool = True,
        include_semantic: bool = True,
    ) -> MemoryContext:
        """
        Retrieve relevant context from all memory tiers.
        Respects max_tokens budget across all tiers.
        """
        await self._init_lazy()
        ctx = MemoryContext()
        tokens_used = 0
        token_budget = max_tokens
        
        # Tier 1: Working memory (always first, most important)
        if self._context_mgr:
            try:
                working = self._context_mgr.get_context_string()
                working_tokens = len(working.split()) * 1.3  # rough estimate
                if working_tokens < token_budget:
                    ctx.working = working
                    tokens_used += int(working_tokens)
                    token_budget -= int(working_tokens)
            except Exception as e:
                logger.debug(f"Working memory read failed: {e}")
        
        # Tier 2: Episodic memory — search past similar tasks
        if include_episodic and self._vector_store and token_budget > 200:
            try:
                similar = await asyncio.wait_for(
                    self._vector_store.retrieve_similar(task, limit=3),
                    timeout=3.0
                )
                if similar:
                    episodic_text = "\n---\n".join(
                        f"Past task: {item.get('text', '')[:300]}"
                        for item in similar[:3]
                    )
                    ep_tokens = len(episodic_text.split()) * 1.3
                    if ep_tokens < token_budget:
                        ctx.episodic = episodic_text
                        tokens_used += int(ep_tokens)
                        token_budget -= int(ep_tokens)
            except asyncio.TimeoutError:
                logger.warning("Episodic memory search timed out (3.0s)")
            except Exception as e:
                logger.debug(f"Episodic memory read failed: {e}")
        
        # Tier 3: Semantic memory — extract entities and find graph facts
        if include_semantic and self._knowledge_graph and token_budget > 100:
            try:
                # Extract key terms from task for graph lookup
                import re
                keywords = re.findall(r'\b[A-Z][a-z]+\b|\b\w{6,}\b', task)[:5]
                facts = []
                for kw in keywords:
                    nodes = await asyncio.wait_for(
                        self._knowledge_graph.search(kw),
                        timeout=3.0
                    ) if hasattr(self._knowledge_graph, 'search') else []
                    if nodes:
                        facts.extend(nodes[:2])
                if facts:
                    semantic_text = "\n".join(str(f)[:100] for f in facts[:5])
                    sem_tokens = len(semantic_text.split()) * 1.3
                    if sem_tokens < token_budget:
                        ctx.semantic = semantic_text
                        tokens_used += int(sem_tokens)
            except asyncio.TimeoutError:
                logger.warning("Semantic memory search timed out (3.0s)")
            except Exception as e:
                logger.debug(f"Semantic memory read failed: {e}")
        
        ctx.total_tokens_est = tokens_used
        return ctx

    async def store(
        self,
        task: str,
        result: str,
        memory_type: str = "episodic",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store task+result in appropriate memory tier."""
        await self._init_lazy()
        
        if memory_type == "episodic" and self._vector_store:
            try:
                # Experience Compression: Summarize result before storing if it's long
                summarized_result = result
                if len(result) > 500:
                    summarized_result = await self._summarize_result(task, result)
                
                fact = f"Task: {task[:300]}\nLessons Learned: {summarized_result}"
                await self._vector_store.add_fact(
                    fact,
                    metadata={"session_id": self.session_id, 
                              "type": "episodic", **(metadata or {})}
                )
                return True
            except Exception as e:
                logger.warning(f"Episodic store failed: {e}")
        
        return False

    async def _summarize_result(self, task: str, result: str) -> str:
        """Compresses task execution result into key findings and lessons."""
        from backend.models.model_router import get_model_router
        router = get_model_router()
        prompt = f"""Summarize the outcome of this task for future reference (Lessons Learned).
Task: {task}
Result: {result}

Extract ONLY the most important technical findings, pitfalls, or verified facts. 
Be extremely concise (max 3 sentences)."""
        try:
            response = await router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="quick"
            )
            return response.get("text", result[:300])
        except Exception:
            return result[:300]

    async def get_context_string(self, task: str, max_tokens: int = 2000) -> str:
        """Convenience method — returns combined context as string."""
        ctx = await self.get_relevant_context(task, max_tokens)
        parts = []
        if ctx.working:
            parts.append(f"[Working Memory]\n{ctx.working}")
        if ctx.episodic:
            parts.append(f"[Relevant Past Experience]\n{ctx.episodic}")
        if ctx.semantic:
            parts.append(f"[Known Facts]\n{ctx.semantic}")
        return "\n\n".join(parts)
