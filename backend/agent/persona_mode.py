class PersonaMode:
    """Активирует режим конкретной личности для сессии."""
    
    async def build_system_prefix(self, persona_desc: str, router) -> str:
        prompt = f"""
Create a system prompt for an AI roleplaying as: {persona_desc}
Include: speaking style, vocabulary, core beliefs, teaching approach, signature phrases.
Return ONLY the system prompt text, nothing else.
"""
        # The router might be Gemini, Groq or Ollama. 
        # Using task_hint="default" to just do standard text generation
        resp = await router.generate(
            messages=[{"role": "user", "content": prompt}],
            task_hint="default"
        )
        return resp.get("text", "")

    async def evolve_persona(
        self, session_id: str, interaction_summary: str
    ):
        """Store personality insights that persist across sessions."""
        from backend.memory.memory_bank import save_fact
        save_fact(
            fact=f"Persona insight: {interaction_summary[:200]}",
            session_id="global",
            category="persona",
            importance=2
        )

    async def get_evolved_persona(self) -> str:
        """Load evolved personality from past interactions."""
        from backend.memory.memory_bank import get_relevant_facts
        insights = get_relevant_facts(
            limit=5, category="persona"
        )
        if not insights:
            return ""
        return (
            "\nPersonality insights from experience:\n"
            + "\n".join(f"• {i}" for i in insights)
        )
