import logging
import os
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import pathlib
import asyncio

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
    Hardened version with Proactive Triggers support.
    """
    _MAX_JOBS = 20
    _MIN_INTERVAL_SECONDS = 60
    _JOB_ID_PATTERN = re.compile(r'^job_[a-zA-Z0-9_-]{1,50}$')
    _VALID_CRON = re.compile(
        r'^(\*|[0-5]?\d)(\s+(\*|[01]?\d|2[0-3]))(\s+(\*|[12]?\d|3[01]))'
        r'(\s+(\*|[1-9]|1[0-2]))(\s+(\*|[0-6]))$'
    )

    def __init__(self):
        self._scheduler = None
        self._jobs: List[Dict[str, Any]] = []
        
        data_dir = pathlib.Path("data")
        data_dir.mkdir(exist_ok=True)
        self._persistence_file = str(data_dir / "scheduler_jobs.json")

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
        except Exception as e:
            logger.error(f"ScheduleTool: Failed to load jobs: {e}")

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            self._reregister_jobs()
            logger.info("ScheduleTool: APScheduler started.")

    def _make_job_fn(self, task_desc: str, session_id: str):
        """
        Create a job function that actually runs the agent.
        Uses safe_create_task to avoid blocking the scheduler loop.
        """
        async def _run_agent_task():
            try:
                from backend.agent.factory import AgentFactory
                agent = AgentFactory.create(session_id=session_id)
                await asyncio.sleep(2)  # Allow init
                
                result = await asyncio.wait_for(
                    agent.process_task(task_desc),
                    timeout=120  # 2 minute max for scheduled tasks
                )
                
                output = getattr(result, 'output', str(result))
                logger.info(
                    f"[Scheduler] Task completed: '{task_desc[:50]}' "
                    f"→ {str(output)[:100]}"
                )
                
                # Emit via EventBus if session has active WebSocket
                try:
                    from backend.agent.orchestration.event_bus import EventBus
                    bus = EventBus.get_instance(session_id)
                    await bus.emit({
                        "type": "proactive_result",
                        "task": task_desc[:100],
                        "output": str(output)[:500],
                        "session_id": session_id,
                    })
                except Exception:
                    pass
                    
            except asyncio.TimeoutError:
                logger.warning(f"[Scheduler] Task timed out: '{task_desc[:50]}'")
            except Exception as e:
                logger.error(f"[Scheduler] Task failed: '{task_desc[:50]}': {e}")
        
        def job_fn():
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_run_agent_task())
                else:
                    asyncio.run(_run_agent_task())
            except Exception as e:
                logger.error(f"[Scheduler] Failed to create task: {e}")
        
        return job_fn

    def _reregister_jobs(self):
        reregistered = 0
        for job in self._jobs:
            try:
                trigger_desc = job.get("trigger", "")
                job_id = job.get("id")
                task_desc = job.get("task", job_id)
                session_id = job.get("session_id", job_id)
                
                job_fn = self._make_job_fn(task_desc, session_id)
                
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
                      session_id: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:

        if not APSCHEDULER_AVAILABLE:
            return {
                "success": False,
                "error": "APScheduler is not installed. Run: pip install apscheduler"
            }

        if action == "add":
            # Validate job count
            if len(self._jobs) >= self._MAX_JOBS:
                return {"success": False, "error": f"Max {self._MAX_JOBS} jobs reached"}
            
            # Validate task_description
            if not task_description or len(task_description) > 500:
                return {"success": False, "error": "task_description required, max 500 chars"}
            
            # Validate interval minimum
            if interval_seconds and interval_seconds < self._MIN_INTERVAL_SECONDS:
                return {"success": False, "error": f"Minimum interval: {self._MIN_INTERVAL_SECONDS}s"}
            
            # Validate cron (if provided)
            if cron and not self._VALID_CRON.match(cron.strip()):
                return {"success": False, "error": "Invalid cron expression"}

            try:
                import uuid
                if not session_id:
                    session_id = f"job_{uuid.uuid4().hex[:8]}"

                job_id = f"job_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

                if cron:
                    trigger = CronTrigger.from_crontab(cron)
                    trigger_desc = f"cron: {cron}"
                elif interval_seconds:
                    trigger = IntervalTrigger(seconds=interval_seconds)
                    trigger_desc = f"every {interval_seconds}s"
                else:
                    return {"success": False, "error": "Provide either 'cron' or 'interval_seconds'."}

                job_fn = self._make_job_fn(task_description, session_id)

                self._scheduler.add_job(job_fn, trigger=trigger, id=job_id)
                self._jobs.append({
                    "id": job_id, 
                    "trigger": trigger_desc, 
                    "task": task_description,
                    "cron": cron,
                    "interval_seconds": interval_seconds,
                    "session_id": session_id
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
            
            # Validate job_id
            if not self._JOB_ID_PATTERN.match(job_id):
                return {"success": False, "error": "Invalid job_id format"}

            try:
                self._scheduler.remove_job(job_id)
                self._jobs = [j for j in self._jobs if j["id"] != job_id]
                self._save_jobs()
                return {"success": True, "output": f"Job '{job_id}' removed."}
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: add, list, remove"}
