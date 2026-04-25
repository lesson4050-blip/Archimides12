import asyncio
import logging
from typing import Any
from backend.agent.skill_library import SkillLibrary

logger = logging.getLogger(__name__)

class SelfPlayLoop:
    def __init__(self, model_router: Any, skill_library: SkillLibrary, idle_threshold_mins: int = 30):
        self.model_router = model_router
        self.skill_library = skill_library
        self.idle_threshold_mins = idle_threshold_mins
        self.last_activity_time = asyncio.get_event_loop().time()
        self._running = False

    def update_activity(self):
        self.last_activity_time = asyncio.get_event_loop().time()

    async def start(self):
        self._running = True
        logger.info(f"SelfPlayLoop started (idle threshold: {self.idle_threshold_mins}m)")
        while self._running:
            await asyncio.sleep(60)
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_activity_time > self.idle_threshold_mins * 60:
                logger.info("Self-Play: Idle threshold reached. Starting synthetic task.")
                await self._run_synthetic_task()
                self.update_activity()

    async def _run_synthetic_task(self):
        prompt = "Generate a challenging synthetic software engineering task that an autonomous agent could solve to improve its skills. Provide only the task description."
        try:
            res = await self.model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            task = res.get("text", "")
            if not task:
                return

            logger.info(f"Self-Play task generated: {task[:60]}")
            
            # Simulated learning step for demonstration
            solution_prompt = f"Solve this task:\n{task}\nProvide the best solution approach."
            sol_res = await self.model_router.generate(
                messages=[{"role": "user", "content": solution_prompt}],
                task_hint="think"
            )
            solution = sol_res.get("text", "")

            if solution:
                self.skill_library.save_skill(task, solution)
                logger.info("Self-Play: New skill learned and added to SkillLibrary.")

        except Exception as e:
            logger.error(f"Self-Play task failed: {e}")

    def stop(self):
        self._running = False
