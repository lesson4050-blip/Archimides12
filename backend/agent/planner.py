from typing import List, Dict, Any

class PlanManager:
    """
    Manages the task plan: a list of phases.
    Phases: id, title, status (pending, active, complete), capabilities
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.phases: List[Dict[str, Any]] = []
        self.current_phase_index: int = -1

    def update_plan(self, phases: List[Dict[str, Any]]):
        """
        Replaces the entire plan.
        """
        self.phases = phases
        self.current_phase_index = 0
        if self.phases:
            for i, phase in enumerate(self.phases):
                if i == 0:
                    phase["status"] = "active"
                else:
                    phase["status"] = "pending"

    def advance_phase(self) -> bool:
        """
        Marks current phase complete and moves to next.
        Returns True if advanced, False if already at end.
        """
        if 0 <= self.current_phase_index < len(self.phases):
            self.phases[self.current_phase_index]["status"] = "complete"
            self.current_phase_index += 1
            if self.current_phase_index < len(self.phases):
                self.phases[self.current_phase_index]["status"] = "active"
                return True
        return False

    def get_plan_data(self) -> List[Dict[str, Any]]:
        return self.phases
