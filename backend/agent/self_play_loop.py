"""
Self-Play Learning Loop.
Агент генерирует синтетические задачи пока простаивает,
решает их, складывает успешные траектории в SkillLibrary.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional
from backend.agent.skill_library import SkillLibrary
from backend.agent.intelligence.cot_engine import inject_cot

logger = logging.getLogger(__name__)

TASK_TEMPLATES = [
    "Write a Python function that {action} with type hints and tests.",
    "Refactor this pattern to be more Pythonic: {pattern}",
    "Design minimal architecture for: {system}",
    "Fix the most common bug in this pattern: {pattern}",
    "Write unit tests for a function that {action}",
]

FILLERS = {
    "action": [
        "validates email addresses",
        "retries async HTTP with backoff",
        "implements LRU cache",
        "parses CSV with custom delimiters",
        "finds all prime numbers to N",
        "implements rate limiter",
        "converts nested dict to flat",
    ],
    "pattern": [
        "nested if-else with 5+ conditions",
        "global variables across functions",
        "string concatenation in loops",
        "catching bare Exception everywhere",
    ],
    "system": [
        "URL shortener with analytics",
        "job queue with priorities",
        "rate limiting middleware",
        "async task scheduler",
    ],
}


class SelfPlayLoop:
    def __init__(
        self,
        router,
        skill_library: SkillLibrary,
        idle_threshold_mins: int = 30,
    ):
        self.router = router
        self.skill_library = skill_library
        self.idle_threshold = timedelta(minutes=idle_threshold_mins)
        self._last_activity = datetime.now()
        self._running = False
        self.sessions = 0
        self.learned = 0

    def update_activity(self):
        self._last_activity = datetime.now()

    def is_idle(self) -> bool:
        return datetime.now() - self._last_activity > self.idle_threshold

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info(
            f"Self-Play: starting (activates after "
            f"{self.idle_threshold.seconds // 60}min idle)"
        )
        asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False

    async def _loop(self):
        while self._running:
            if self.is_idle():
                await self._run_session()
            else:
                await asyncio.sleep(300)

    async def _run_session(self):
        task = self._generate_task()
        try:
            messages = inject_cot(
                [{"role": "user", "content": task}], task
            )
            resp = await asyncio.wait_for(
                self.router.generate(
                    messages=messages, task_hint="quality"
                ),
                timeout=60.0,
            )
            solution = resp.get("text", "").strip()
            if len(solution) < 50:
                return

            quality = await self._score(task, solution)
            if quality >= 7.0:
                steps = [
                    {"step": 1, "action": task[:80], "tool": "router"},
                    {"step": 2, "action": "verify quality", "tool": "scorer"},
                ]
                skill_id = await self.skill_library.compress_workflow(
                    task=task,
                    steps_executed=steps,
                    result_quality=quality,
                    router=self.router,
                )
                if skill_id:
                    self.learned += 1
                    logger.info(
                        f"Self-Play: learned '{skill_id}' "
                        f"(quality {quality:.1f}/10)"
                    )

            self.sessions += 1
            await asyncio.sleep(random.uniform(60, 180))
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.warning(f"Self-Play session failed: {e}")
            await asyncio.sleep(60)

    def _generate_task(self) -> str:
        template = random.choice(TASK_TEMPLATES)
        for key, options in FILLERS.items():
            if f"{{{key}}}" in template:
                template = template.replace(
                    f"{{{key}}}", random.choice(options)
                )
        return template

    async def _score(self, task: str, solution: str) -> float:
        prompt = (
            f"Rate this solution 0-10.\n"
            f"TASK: {task[:200]}\n"
            f"SOLUTION: {solution[:500]}\n"
            f"Return JSON only: {{\"score\": 7.5}}"
        )
        try:
            from backend.utils.json_repair import repair_and_parse
            resp = await asyncio.wait_for(
                self.router.generate(
                    messages=[{"role": "user", "content": prompt}],
                    task_hint="fast",
                ),
                timeout=20.0,
            )
            data, _ = repair_and_parse(resp.get("text", "{}"))
            if data and isinstance(data.get("score"), (int, float)):
                return float(data["score"])
        except (asyncio.TimeoutError, ValueError, KeyError) as e:
            logger.debug(f"Self-play scoring failed: {e}")
        return 5.0

    def get_stats(self) -> dict:
        return {
            "sessions": self.sessions,
            "learned": self.learned,
            "idle": self.is_idle(),
        }
