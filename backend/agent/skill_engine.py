"""
Legacy SkillEngine Proxy.
Redirects calls to the unified SkillEngine in backend.agent.skills.
This file exists to maintain backward compatibility while migrating to the new class-based engine.
"""
import logging
from backend.agent.skills.skill_engine import SkillEngine

logger = logging.getLogger(__name__)

# Singleton instance for backward compatibility
_engine = SkillEngine()

def extract_and_save_skill(task_description, history, success=True):
    """Bridge to the new SkillEngine.extract_and_save_skill"""
    return _engine.extract_and_save_skill(task_description, history, success)

def find_matching_skill(task_description, threshold=0.7):
    """Bridge to the new SkillEngine.find_relevant_skill"""
    return _engine.find_relevant_skill(task_description, threshold)

def get_skill_prompt(skill):
    """Bridge to the new SkillEngine.get_skill_prompt_injection"""
    return _engine.get_skill_prompt_injection(skill)

def compress_skill(steps):
    """
    Legacy stub. New engine handles compression during extraction.
    Returning templatized steps for safety.
    """
    templated, vars = _engine._advanced_templatize(steps)
    return templated
