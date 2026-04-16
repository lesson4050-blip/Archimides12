import logging
import os
import json
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
        self._persistence_file = "scheduler_jobs.json"

        if APSCHEDULER_AVAILABLE:
            self._scheduler = AsyncIOScheduler()
            self._load_jobs()

    def _save_jobs(self):
        """Save current jobs to a JSON file."""
        try:
            with open(self._persistence_file, "w") as f:
                json.dump(self._jobs, f)
            logger.info(f"ScheduleTool: Jobs saved to {self._persistence_file}")
        except Exception as e:
            logger.error(f"ScheduleTool: Failed to save jobs: {e}")

    def _load_jobs(self):
        """Load jobs from a JSON file and re-register them."""
        if not os.path.exists(self._persistence_file):
            return

        try:
            with open(self._persistence_file, "r") as f:
                self._jobs = json.load(f)
            logger.info(f"ScheduleTool: Loaded {len(self._jobs)} jobs from {self._persistence_file}")
            
            # Note: We don't re-register yet because scheduler needs to be started
            # Registration will happen if we start the scheduler or on demand
        except Exception as e:
            logger.error(f"ScheduleTool: Failed to load jobs: {e}")

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            self._reregister_jobs()
            logger.info("ScheduleTool: APScheduler started.")

    def _reregister_jobs(self):
        reregistered = 0
        for job in self._jobs:
            try:
                trigger_desc = job.get("trigger", "")
                job_id = job.get("id")
                def job_fn(desc=job.get("task", job_id)):
                    logger.info(f"Scheduled job triggered: {desc}")
                if trigger_desc.startswith("cron:"):
                    cron_expr = trigger_desc.replace("cron: ", "").strip()
                    trigger = CronTrigger.from_crontab(cron_expr)
                elif trigger_desc.startswith("every"):
                    seconds = int(''.join(filter(str.isdigit, trigger_desc)))
                    trigger = IntervalTrigger(seconds=seconds)
                else:
                    continue
                self._scheduler.add_job(job_fn, trigger=trigger, id=job_id)
                reregistered += 1
            except Exception as e:
                logger.warning(f"Could not re-register job {job.get('id')}: {e}")
        if reregistered:
            logger.info(f"ScheduleTool: Re-registered {reregistered} persisted jobs.")

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
                self._jobs.append({
                    "id": job_id, 
                    "trigger": trigger_desc, 
                    "task": task_description,
                    "cron": cron,
                    "interval_seconds": interval_seconds
                })
                self._save_jobs()

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
                self._save_jobs()
                return {"success": True, "output": f"Job '{job_id}' removed."}
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: add, list, remove"}
