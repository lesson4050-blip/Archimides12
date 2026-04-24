import logging
from typing import Dict, Any, List
from backend.agent.intelligence.cot_engine import inject_cot, extract_cot_answer
from backend.agent.intelligence.moa_engine import MixtureOfAgents
from backend.agent.intelligence.reflection_engine import ReflectionEngine
from backend.agent.intelligence.self_consistency import SelfConsistency

logger = logging.getLogger(__name__)

class IntelligenceRouter:
    def __init__(self, model_router):
        self.router = model_router
        self.moa = MixtureOfAgents(model_router)
        self.reflection = ReflectionEngine(model_router)
        self.sc = SelfConsistency(model_router)

    async def _classify_complexity_llm(self, task: str) -> str:
        if not task: return "simple"
        prompt = (
            f"Classify the complexity of this task into one word: 'simple', 'medium', or 'complex'.\n"
            f"- simple: basic API calls, status checks, formatting.\n"
            f"- medium: writing a function, fixing a bug, data analysis.\n"
            f"- complex: system architecture, comprehensive research, deep refactoring.\n\n"
            f"Task: {task[:500]}\nOutput ONLY ONE WORD."
        )
        try:
            res = await self.router.generate([{"role": "user", "content": prompt}], task_hint="fast", max_tokens=5)
            ans = res.get("text", "").lower().strip()
            if "complex" in ans: return "complex"
            if "medium" in ans: return "medium"
            return "simple"
        except:
            return "medium"

    async def generate(self, messages: List[Dict], task: str = "", force_mode: str = None, tools: List[Dict] = None, on_token=None) -> Dict[str, Any]:
        mode = force_mode or await self._classify_complexity_llm(task)
        logger.info(f"Intelligence mode: [{mode}]")

        if mode == "simple":
            cot_messages = inject_cot(messages, task)
            if on_token:
                result = await self.router.generate_stream(messages=cot_messages, tools=tools, task_hint="fast", on_token=on_token)
            else:
                result = await self.router.generate(messages=cot_messages, tools=tools, task_hint="fast")
            
            parsed = extract_cot_answer(result.get("text", ""))
            return {**result, "text": parsed["answer"], "thinking": parsed["thinking"], "intelligence_mode": "cot_direct"}

        elif mode == "medium":
            cot_messages = inject_cot(messages, task)
            initial = await self.router.generate(messages=cot_messages, tools=tools, task_hint="quality")
            parsed = extract_cot_answer(initial.get("text", ""))
            
            reflected = await self.reflection.reflect_and_improve(
                original_messages=messages, initial_response=parsed["answer"], task=task
            )
            return {**initial, **reflected, "intelligence_mode": "cot_reflection", "thinking": parsed["thinking"]}

        else: 
            cot_messages = inject_cot(messages, task)
            moa_result = await self.moa.generate(messages=cot_messages, task=task, min_proposers=3)
            
            reflected = await self.reflection.reflect_and_improve(
                original_messages=messages, initial_response=moa_result["text"], task=task
            )
            return {**moa_result, **reflected, "intelligence_mode": "moa_cot_reflection", "proposer_count": moa_result.get("proposer_count", 1)}
