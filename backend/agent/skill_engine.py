"""
Legacy SkillEngine Proxy.
Redirects calls to the real SkillEngine in backend.agent.skill_library.
"""
import logging
from typing import List, Dict, Any, Optional
from backend.agent.skill_library import SkillLibrary as SkillEngine

logger = logging.getLogger(__name__)

_engine = SkillEngine()

def extract_and_save_skill(task_description: str, history: List[Dict[str, Any]], success: bool = True) -> None:
    """Extracts a skill from a successful task history and saves it."""
    return _engine.store_skill(task_description, history, quality_score=1.0 if success else 0.0)

def find_matching_skill(task_description: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
    """Finds a matching skill in the library for the given task description."""
    return _engine.find_skill(task_description)

def get_skill_prompt(skill: Dict[str, Any]) -> str:
    """Generates a prompt snippet from a skill dictionary."""
    # Note: SkillLibrary.get_context_prompt takes a task string, 
    # but this proxy is used for raw formatting.
    steps = skill.get("trajectory", [])
    lines = ["[SKILL ADVICE]"]
    for i, step in enumerate(steps[:5], 1):
        lines.append(f"  Step {i}: {step.get('tool','')} -> {step.get('result_summary','')[:100]}")
    return "\n".join(lines)

def compress_skill(steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Compresses a trajectory into a storage-efficient format."""
    return _engine._compress_trajectory(steps)
