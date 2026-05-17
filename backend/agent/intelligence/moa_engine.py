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

        # Slice configs based on min_proposers
        configs_to_run = proposer_configs[:max(min_proposers, len(proposer_configs))]
        proposals = await asyncio.gather(
            *[run_proposer(c) for c in configs_to_run],
            return_exceptions=True
        )
        valid = [
            p for p in proposals
            if isinstance(p, str) and not isinstance(p, BaseException) and len(p) > 5
        ]

        if not valid:
            return await self.router.generate(messages=messages)
        if len(valid) == 1:
            return {"text": valid[0], "model": "moa_single", "consensus_hit": True}

        # FAST PATH (Speculative Execution / Consensus Check)
        # If all proposers return exactly the same logic (or >95% similar), skip synthesis
        import difflib
        if len(valid) >= 2:
            sim1 = difflib.SequenceMatcher(None, valid[0], valid[1]).ratio()
            sim2 = difflib.SequenceMatcher(None, valid[0], valid[-1]).ratio()
            if sim1 > 0.95 and sim2 > 0.95:
                logger.info("MoA FAST PATH hit: High consensus (>95%). Skipping synthesis.")
                return {"text": valid[0], "model": "moa_fast_path", "proposer_count": len(valid), "consensus_hit": True}

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

    async def council(
        self,
        messages: List[Dict],
        task: str = "",
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Model Council — runs multiple model configs in parallel.
        Returns ALL responses (not synthesized) for user comparison.
        
        SECURITY: timeout enforced per-proposer to prevent hanging.
        SECURITY: output length capped to prevent memory bloat.
        """
        MAX_OUTPUT_LENGTH = 4000  # chars per model response
        
        council_configs = [
            {"temp": 0.7, "hint": "fast",    "label": "Creative"},
            {"temp": 0.3, "hint": "quality", "label": "Precise"},
            {"temp": 0.5, "hint": "default", "label": "Balanced"},
        ]
        
        async def run_council_member(config: dict) -> dict:
            label = config["label"]
            try:
                resp = await asyncio.wait_for(
                    self.router.generate(
                        messages=messages,
                        task_hint=config["hint"],
                        temperature=config["temp"]
                    ),
                    timeout=timeout_seconds
                )
                text = resp.get("text", "").strip()
                # Security: cap output length
                if len(text) > MAX_OUTPUT_LENGTH:
                    text = text[:MAX_OUTPUT_LENGTH] + "\n...[truncated]"
                
                return {
                    "label": label,
                    "model": resp.get("model_used", "unknown"),
                    "text": text,
                    "tokens": resp.get("usage", {}).get("total_tokens", 0),
                    "success": bool(text),
                    "error": None,
                }
            except asyncio.TimeoutError:
                logger.warning(f"Council member '{label}' timed out after {timeout_seconds}s")
                return {
                    "label": label,
                    "model": "timeout",
                    "text": "",
                    "success": False,
                    "error": f"Timed out after {timeout_seconds}s",
                }
            except Exception as e:
                logger.warning(f"Council member '{label}' failed: {e}")
                return {
                    "label": label,
                    "model": "error",
                    "text": "",
                    "success": False,
                    "error": str(e)[:200],  # Cap error message length
                }
        
        results = await asyncio.gather(
            *[run_council_member(c) for c in council_configs]
        )
        
        successful = [r for r in results if r["success"]]
        
        return {
            "type": "council",
            "task": task[:500],  # Cap task length in response
            "responses": list(results),  # All responses including failures
            "successful_count": len(successful),
            "total_count": len(results),
        }
