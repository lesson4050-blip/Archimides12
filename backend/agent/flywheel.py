import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DataFlywheel:
    """
    Data Flywheel: Captures execution traces and feedback for RLHF fine-tuning.
    Records successful trajectories to teach the model optimal paths, and failed ones
    to teach it what to avoid.
    """
    
    def __init__(self, dataset_path: str = "data/flywheel.jsonl"):
        self.dataset_path = dataset_path
        os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)
        
    def record_session(self, session_id: str, task: str, result: Dict[str, Any], history: list):
        """Records the session outcome for future fine-tuning."""
        try:
            record = {
                "session_id": session_id,
                "task": task,
                "success": result.get("success", False),
                "strategy": result.get("strategy", "unknown"),
                "history": history,
                "final_output": result.get("output", ""),
            }
            with open(self.dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.info(f"Flywheel: Recorded session {session_id} (Success: {record['success']})")
        except Exception as e:
            logger.error(f"Flywheel failed to record session {session_id}: {e}")

# Global instance
flywheel = DataFlywheel()
