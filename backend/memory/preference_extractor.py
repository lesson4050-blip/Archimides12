"""
Extracts user preferences from conversation and stores them permanently.
Called after each completed task.

Preferences examples:
  - "User prefers Python over JavaScript"
  - "User works on Windows with RTX 3060"
  - "User wants concise answers without filler"
  - "User's project is Archimedes at d:/Cosmo"
"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

PREFERENCE_PATTERNS = [
    # Explicit preferences
    (r"(i prefer|i like|i want|i need|i use|i work with|i always)\s+(.{10,80})", "preference"),
    # Technical setup
    (r"(my (project|repo|workspace|machine|setup|stack) is|i'm (using|running|working on))\s+(.{5,60})", "setup"),
    # Language preferences
    (r"(always use|use only|stick to|prefer)\s+(python|javascript|typescript|rust|go|java)\b", "language"),
    # Style preferences
    (r"(give me|show me|i want)\s+(short|brief|concise|detailed|verbose|simple)\s+answers?", "style"),
]

class PreferenceExtractor:
    """Extracts and stores user preferences from conversation history."""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
    
    async def extract_and_store(self, messages: List[Dict]) -> List[str]:
        """
        Scan recent messages for user preferences.
        Store any found preferences in vector store for future recall.
        Returns list of extracted preferences.
        """
        extracted = []
        
        user_messages = [
            m.get("content", "") for m in messages 
            if m.get("role") == "user" and isinstance(m.get("content"), str)
        ]
        
        for message in user_messages[-5:]:  # Only scan last 5 user messages
            for pattern, pref_type in PREFERENCE_PATTERNS:
                matches = re.findall(pattern, message, re.IGNORECASE)
                for match in matches:
                    preference = match[-1] if isinstance(match, tuple) else match
                    preference = preference.strip()
                    if len(preference) > 5:
                        fact = f"User preference ({pref_type}): {preference}"
                        extracted.append(fact)
                        try:
                            await self.vector_store.add_fact(
                                text=fact,
                                metadata={"type": "user_preference", "pref_type": pref_type}
                            )
                        except Exception as e:
                            logger.debug(f"Preference store failed: {e}")
        
        if extracted:
            logger.info(f"Extracted {len(extracted)} user preferences")
        
        return extracted

    async def get_user_preferences(self, context: str = "") -> str:
        """Retrieve relevant user preferences for current context."""
        try:
            prefs = await self.vector_store.retrieve_similar(
                query=f"user preference {context}",
                limit=5
            )
            pref_facts = [
                p.get("document", p.get("text", "")) 
                for p in prefs 
                if "preference" in str(p.get("metadata", {}).get("type", ""))
            ]
            if pref_facts:
                return "User preferences:\n" + "\n".join(f"- {p}" for p in pref_facts[:5])
        except Exception:
            pass
        return ""
