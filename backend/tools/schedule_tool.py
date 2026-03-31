import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


class ScheduleTool:
    """
    Schedules tasks for periodic execution using APScheduler.
    """
    def __init__(self):
        self._scheduler = None
        self._jobs: List[Dict[str, Any]] = []

        if APSCHEDULER_AVAILABLE:
            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
            logger.info("ScheduleTool: APScheduler started.")

    async def execute(self, action: str, cron: Optional[str] = None,
                      interval_seconds: Optional[int] = None,
                      task_description: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:

        if not APSCHEDULER_AVAILABLE:
            return {
                "success": False,
                "error": "APScheduler is not installed. Run: pip install apscheduler"
            }

        if action == "add":
            try:
                job_id = f"job_{len(self._jobs) + 1}_{datetime.now().timestamp()}"

                if cron:
                    trigger = CronTrigger.from_crontab(cron)
                    trigger_desc = f"cron: {cron}"
                elif interval_seconds:
                    trigger = IntervalTrigger(seconds=interval_seconds)
                    trigger_desc = f"every {interval_seconds}s"
                else:
                    return {"success": False, "error": "Provide either 'cron' or 'interval_seconds'."}

                # Register a placeholder job (logs the task description)
                def job_fn():
                    logger.info(f"Scheduled job triggered: {task_description or job_id}")

                self._scheduler.add_job(job_fn, trigger=trigger, id=job_id)
                self._jobs.append({"id": job_id, "trigger": trigger_desc, "task": task_description})

                return {
                    "success": True,
                    "output": f"Job '{job_id}' scheduled ({trigger_desc}). Task: {task_description}"
                }

            except Exception as e:
                return {"success": False, "error": str(e)}

        elif action == "list":
            if not self._jobs:
                return {"success": True, "output": "No scheduled jobs."}
            job_list = "\n".join([
                f"- {j['id']}: {j['trigger']} | {j['task']}" for j in self._jobs
            ])
            return {"success": True, "output": f"Scheduled jobs:\n{job_list}"}

        elif action == "remove":
            job_id = kwargs.get("job_id")
            if not job_id:
                return {"success": False, "error": "Provide 'job_id' to remove."}
            try:
                self._scheduler.remove_job(job_id)
                self._jobs = [j for j in self._jobs if j["id"] != job_id]
                return {"success": True, "output": f"Job '{job_id}' removed."}
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: add, list, remove"}
