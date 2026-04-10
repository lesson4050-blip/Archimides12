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
