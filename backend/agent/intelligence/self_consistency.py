import asyncio
import logging
import difflib
from typing import Dict, Any, List, Optional
from backend.agent.intelligence.cot_engine import extract_cot_answer

logger = logging.getLogger(__name__)

def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

class SelfConsistency:
    def __init__(self, router):
        self.router = router

    async def generate(self, messages: List[Dict], n_samples: int = 3, task_hint: str = "default") -> Dict[str, Any]:
        temperatures = [0.2, 0.5, 0.8][:n_samples]

        async def sample(temp: float) -> Optional[str]:
            try:
                r = await self.router.generate(messages=messages, task_hint=task_hint, temperature=temp)
                parsed = extract_cot_answer(r.get("text", ""))
                return parsed["answer"].strip()
            except Exception as e:
                logger.warning(f"SC sample failed: {e}")
                return None

        samples = await asyncio.gather(*[sample(t) for t in temperatures])
        valid = [s for s in samples if s and len(s) > 5]

        if not valid:
            return await self.router.generate(messages=messages)
        if len(valid) == 1:
            return {"text": valid[0], "model": "sc_single"}

        scores = []
        for i, s in enumerate(valid):
            avg_sim = sum(_similarity(s, o) for j, o in enumerate(valid) if j != i) / max(len(valid) - 1, 1)
            scores.append((avg_sim, s))

        scores.sort(reverse=True)
        return {
            "text": scores[0][1],
            "model": "self_consistency",
            "sample_count": len(valid),
            "consensus_score": round(scores[0][0], 2),
        }
