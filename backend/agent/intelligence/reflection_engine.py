import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

REFLECTION_PROMPT = """Review your previous response and improve it.

ORIGINAL TASK:
{task}

YOUR PREVIOUS RESPONSE:
{response}

CRITIQUE CHECKLIST:
- COMPLETE? (nothing important missing)
- CORRECT? (no factual errors, no wrong code)
- CLEAR? (reader immediately understands)
- CONCISE? (no unnecessary verbosity)
- SOLVES the original task?
- FORMAT: Does it strictly follow the requested JSON/output format?

FORMAT:
ISSUES FOUND: [list problems or "None"]
IMPROVED RESPONSE:
[your better answer in the exact requested format]"""

class ReflectionEngine:
    def __init__(self, router):
        self.router = router

    async def reflect_and_improve(self, original_messages: List[Dict], initial_response: str, task: str = "") -> Dict[str, Any]:
        if len(initial_response) < 100:
            return {"text": initial_response, "reflected": False, "reason": "too_short"}

        reflection_messages = [
            *original_messages,
            {"role": "assistant", "content": initial_response},
            {"role": "user", "content": REFLECTION_PROMPT.format(task=task[:500] or "See above", response=initial_response[:2000])}
        ]

        try:
            improved = await self.router.generate(messages=reflection_messages, task_hint="quality", temperature=0.3)
            text = improved.get("text", "")

            if "IMPROVED RESPONSE:" in text:
                result = text.split("IMPROVED RESPONSE:", 1)[1].strip()
            else:
                result = text

            if len(result) < 50:
                return {"text": initial_response, "reflected": False}

            issues = ""
            if "ISSUES FOUND:" in text:
                issues = text.split("ISSUES FOUND:", 1)[1].split("IMPROVED RESPONSE:")[0].strip()

            return {"text": result, "reflected": True, "issues_found": issues, "original": initial_response}
        except Exception as e:
            logger.warning(f"Reflection failed: {e}")
            return {"text": initial_response, "reflected": False}
