"""
Memory Consolidator — runs nightly (or on demand) to compress episodic
memory into semantic facts. Like human sleep consolidation.

Converts: raw task history → distilled reusable knowledge
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    Compresses episodic task memory into reusable semantic knowledge.
    
    Process:
    1. Load recent task results from memory bank
    2. Cluster by topic/domain
    3. Extract generalizable patterns
    4. Store as high-priority facts
    5. Prune low-value episodic memories
    """
    
    def __init__(self, router, session_id: str = "global"):
        self.router = router
        self.session_id = session_id
    
    async def consolidate(self, max_facts_to_process: int = 20) -> Dict[str, Any]:
        """Run memory consolidation pass."""
        from backend.memory.memory_bank import get_relevant_facts, save_fact, delete_fact
        
        logger.info("Memory consolidation started...")
        
        try:
            # Load recent episodic memories
            recent_facts = await get_relevant_facts(
                limit=max_facts_to_process,
                category="task_result"
            )
            
            if len(recent_facts) < 5:
                return {
                    "success": True,
                    "message": "Not enough memories to consolidate",
                    "processed": 0
                }
            
            # Ask LLM to extract patterns
            consolidation_prompt = (
                "You are a memory consolidation system. "
                "Analyze these task results and extract GENERALIZABLE RULES "
                "that would help solve similar tasks in the future.\n\n"
                "RAW MEMORIES:\n"
                + "\n".join(f"- {f}" for f in recent_facts[:20])
                + "\n\nExtract 3-5 high-value rules/patterns. "
                "Each rule should be:\n"
                "- Generalizable (not task-specific)\n"
                "- Actionable (tells agent what TO DO)\n"
                "- Concise (max 150 chars)\n\n"
                'Output as JSON array: ["rule1", "rule2", ...]'
            )
            
            response = await self.router.generate(
                messages=[{"role": "user", "content": consolidation_prompt}],
                task_hint="think"
            )
            
            from backend.utils.json_repair import repair_and_parse
            rules, _ = repair_and_parse(response.get("text", "[]"))
            
            if not isinstance(rules, list):
                rules = []
            
            # Save consolidated rules as high-priority facts
            saved = 0
            for rule in rules[:5]:
                if isinstance(rule, str) and len(rule) > 10:
                    await save_fact(
                        fact=f"[CONSOLIDATED] {rule}",
                        session_id="global",  # Global — available to all sessions
                        category="consolidated_knowledge",
                        importance=5  # High priority
                    )
                    saved += 1
            
            consolidation_time = datetime.now().isoformat()
            logger.info(
                f"Memory consolidation complete: "
                f"{saved} rules extracted from {len(recent_facts)} memories"
            )
            
            return {
                "success": True,
                "processed": len(recent_facts),
                "rules_extracted": saved,
                "rules": rules[:5],
                "timestamp": consolidation_time
            }
            
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def schedule_nightly(router, interval_hours: int = 24):
        """Run consolidation on a schedule. Call once at startup."""
        consolidator = MemoryConsolidator(router)
        while True:
            await asyncio.sleep(interval_hours * 3600)
            await consolidator.consolidate()
