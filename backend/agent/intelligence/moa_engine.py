import asyncio
import logging
from typing import Dict, Any, List, Optional
from backend.agent.intelligence.cot_engine import extract_cot_answer

logger = logging.getLogger(__name__)

class MixtureOfAgents:
    def __init__(self, router):
        self.router = router

    async def generate(self, messages: List[Dict], task: str = "", min_proposers: int = 2) -> Dict[str, Any]:
        proposer_configs = [
            {"temp": 0.7, "hint": "fast"},
            {"temp": 0.3, "hint": "quality"},
            {"temp": 0.5, "hint": "default"},
        ]

        async def run_proposer(config: dict) -> Optional[str]:
            try:
                resp = await self.router.generate(messages=messages, task_hint=config["hint"], temperature=config["temp"])
                parsed = extract_cot_answer(resp.get("text", ""))
                text = parsed["answer"].strip()
                return text if len(text) > 5 else None
            except Exception as e:
                logger.warning(f"MoA proposer failed: {e}")
                return None

        proposals = await asyncio.gather(*[run_proposer(c) for c in proposer_configs], return_exceptions=True)
        valid = [p for p in proposals if p and isinstance(p, str)]

        if not valid:
            return await self.router.generate(messages=messages)
        if len(valid) == 1:
            return {"text": valid[0], "model": "moa_single"}

        synthesis_prompt = self._build_synthesis_prompt(task, valid, messages)
        try:
            synthesized = await self.router.generate(
                messages=[{"role": "user", "content": synthesis_prompt}],
                task_hint="quality",
            )
            return {"text": synthesized.get("text", valid[0]), "model": "moa", "proposer_count": len(valid)}
        except Exception as e:
            return {"text": max(valid, key=len), "model": "moa_fallback"}

    def _build_synthesis_prompt(self, task: str, proposals: List[str], original_messages: List[Dict]) -> str:
        proposals_text = "\n\n".join([f"--- PROPOSAL {i+1} ---\n{p}" for i, p in enumerate(proposals)])
        
        system_rules = ""
        for m in original_messages:
            if m.get("role") == "system":
                system_rules += str(m.get("content", "")) + "\n"

        return (
            f"You are an expert synthesizer. You received {len(proposals)} proposed solutions for a task.\n\n"
            f"SYSTEM RULES AND EXPECTED FORMAT:\n{system_rules[:1000]}\n\n"
            f"PROPOSALS:\n{proposals_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Evaluate the proposals for correctness and logic.\n"
            f"2. Synthesize the single best answer.\n"
            f"3. CRITICAL: You MUST return the final answer in the EXACT format required by the System Rules (e.g., JSON, markdown). Do NOT add meta-commentary.\n\n"
            f"FINAL SYNTHESIZED OUTPUT:"
        )
