"""
OmnimodalContextBridge — Auto-inject perception into agent context.

When a user uploads ANY file, this bridge:
1. Silently ingests it via OmnimodalIngester
2. Queries for most relevant perceptions for current task
3. Injects compact perception summary into agent context
   (not the raw file, just the semantic understanding)

This is the key architectural shift:
Agent no longer "sees files" — it "queries concepts".
"""
import logging
from typing import Dict, Any, List, Optional
from backend.agent.omnimodal_ingester import OmnimodalIngester, PerceptionUnit

logger = logging.getLogger(__name__)


class OmnimodalContextBridge:
    """
    Bridges file uploads to agent context via vector retrieval.
    """
    
    def __init__(self, ingester: OmnimodalIngester):
        self.ingester = ingester
        self._session_perceptions: Dict[str, List[str]] = {}
    
    async def process_upload(
        self,
        file_path: str,
        session_id: str,
        task_context: str = ""
    ) -> str:
        """
        Process an uploaded file and return context string for agent.
        
        Returns: formatted string ready for injection into LLM context
        """
        # Ingest the file
        unit = await self.ingester.ingest(file_path)
        
        # Track for this session
        if session_id not in self._session_perceptions:
            self._session_perceptions[session_id] = []
        self._session_perceptions[session_id].append(unit.unit_id)
        
        # Get related perceptions if we have context
        related_context = ""
        if task_context:
            related = await self.ingester.query(
                query=task_context,
                top_k=3
            )
            if related:
                related_context = "\n\nRelated perceptions from memory:\n" + \
                    "\n".join(r.to_context_string() for r in related[:2])
        
        return (
            f"[NEW PERCEPTION INGESTED]\n"
            f"{unit.to_context_string()}"
            f"{related_context}"
        )
    
    async def get_session_context(
        self,
        session_id: str,
        current_task: str = "",
        max_perceptions: int = 3
    ) -> str:
        """
        Get all relevant perceptions for current task in a session.
        Injected at the beginning of each agent run.
        """
        if current_task:
            perceptions = await self.ingester.query(
                query=current_task,
                top_k=max_perceptions
            )
        else:
            perceptions = []
        
        if not perceptions:
            return ""
        
        lines = ["[OMNIMODAL MEMORY — relevant perceptions for this task]"]
        for p in perceptions:
            lines.append(p.to_context_string())
        lines.append("[END OMNIMODAL MEMORY]")
        
        return "\n".join(lines)
