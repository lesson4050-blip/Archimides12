"""
Legacy SkillEngine Proxy.
Redirects calls to the real SkillEngine in backend.agent.skill_library.
"""
import logging
from backend.agent.skill_library import SkillLibrary as SkillEngine

logger = logging.getLogger(__name__)

_engine = SkillEngine()

def extract_and_save_skill(task_description, history, success=True):
    return _engine.extract_and_save_skill(task_description, history, success)

def find_matching_skill(task_description, threshold=0.7):
    return _engine.find_relevant_skill(task_description, threshold)

def get_skill_prompt(skill):
    return _engine.get_skill_prompt_injection(skill)

def compress_skill(steps):
    templated, variables = _engine._advanced_templatize(steps)
    return templated
