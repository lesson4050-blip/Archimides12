import logging
from typing import Dict, Any
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)

PERSONA_TEMPLATES = [
    {"age": 25, "type": "tech_enthusiast", "region": "urban", "income": "medium"},
    {"age": 45, "type": "conservative_manager", "region": "suburban", "income": "high"},
    {"age": 32, "type": "startup_founder", "region": "urban", "income": "high"},
    {"age": 55, "type": "traditional_consumer", "region": "rural", "income": "low"},
    {"age": 28, "type": "activist", "region": "urban", "income": "low"},
    {"age": 38, "type": "pragmatic_parent", "region": "suburban", "income": "medium"},
]

class MiroFishTool:
    """
    Симулирует реакцию разных типов людей на идею/продукт/гипотезу.
    Использует LLM для генерации персонажей и их реакций — без внешних API.
    """
    
    def __init__(self):
        self.router = ModelRouter()
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "mirofish",
                "description": (
                    "Simulate public reaction to a HYPOTHETICAL idea, product, or scenario. "
                    "Generates diverse personas and their honest reactions. "
                    "Use this for 'What if' scenarios or testing new concepts. "
                    "Returns sentiment, key objections, adoption probability."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hypothesis": {"type": "string", "description": "Idea to test"},
                        "context": {"type": "string", "description": "Target audience or context"},
                        "num_personas": {"type": "integer", "default": 6, "minimum": 3, "maximum": 10}
                    },
                    "required": ["hypothesis"]
                }
            }
        }

    async def execute(self, hypothesis: str = "", context: str = "",
                      num_personas: int = 6, **kwargs) -> Dict[str, Any]:
        if not hypothesis:
            return {"success": False, "error": "Hypothesis is required for MiroFish simulation."}
        personas = PERSONA_TEMPLATES[:num_personas]
        
        # Параллельно симулируем реакцию каждого персонажа
        async def simulate_persona(persona: dict) -> dict:
            prompt = f"""
You are a {persona['age']}-year-old {persona['type']} from a {persona['region']} area with {persona['income']} income.
React to this idea honestly from your perspective: "{hypothesis}"
Context: {context}

Respond in JSON:
{{
  "reaction": "positive|negative|neutral",
  "comment": "your honest 1-2 sentence reaction",
  "would_adopt": true/false,
  "main_objection": "your biggest concern or null"
}}
Return ONLY valid JSON, no other text.
"""
            resp = await self.router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="default"
            )
            try:
                text = resp.get("text", "{}").strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                from backend.utils.json_repair import repair_and_parse
                data, err = repair_and_parse(text.strip())
                if data is None:
                    logger.error(f"MiroFish: failed to parse persona response: {err}")
                    return {**persona, "reaction": "neutral", "would_adopt": False, "comment": "Parse error.", "main_objection": None}
                return {**persona, **data}
            except Exception as e:
                logger.error(f"MiroFish parse error fallback: {e}")
                return {**persona, "reaction": "neutral", "would_adopt": False, "comment": "Failed to parse reaction."}
        
        results = []
        for p in personas:
            res = await simulate_persona(p)
            results.append(res)
        
        # Агрегация
        positive = sum(1 for r in results if r.get("reaction") == "positive")
        negative = sum(1 for r in results if r.get("reaction") == "negative")
        adopters = sum(1 for r in results if r.get("would_adopt"))
        objections = [r["main_objection"] for r in results 
                      if r.get("main_objection") and r.get("main_objection") != "null"]
        
        overall_sentiment = "positive" if positive > negative else \
                           "negative" if negative > positive else "mixed"
        adoption_prob = round(adopters / len(results) * 100)
        
        summary = (
            f"Simulation ({len(results)} personas):\n"
            f"Sentiment: {overall_sentiment} ({positive}+ / {negative}-)\n"
            f"Adoption probability: {adoption_prob}%\n"
            f"Top objections: {'; '.join(objections[:3]) if objections else 'None'}\n\n"
            f"Persona reactions:\n" +
            "\n".join([f"- {r['type']} ({r['age']}y): {r.get('comment', '')}" 
                       for r in results])
        )
        
        return {
            "success": True,
            "output": summary,
            "sentiment": overall_sentiment,
            "adoption_probability": adoption_prob,
            "key_objections": objections
        }
