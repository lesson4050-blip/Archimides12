import logging
from backend.tools.schedule_tool import ScheduleTool

logger = logging.getLogger(__name__)

# Global instance
scheduler_instance = ScheduleTool()

def get_scheduler():
    return scheduler_instance
