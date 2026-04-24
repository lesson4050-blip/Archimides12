"""
Archimedes Skill Compression Engine (Sprint 4.1).

When the agent completes a complex multi-step task successfully,
this engine can compress the execution trace into a reusable
"skill" file stored in `skills/`.

A skill file captures:
- The original intent/trigger
- The sequence of tool calls and their parameters
- Key decision points and error recovery patterns
- Expected outcomes

The agent can later recall and replay these skills when
encountering similar tasks, dramatically reducing latency
and improving reliability.
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join("data", "skills")


def _ensure_dir():
    os.makedirs(SKILLS_DIR, exist_ok=True)


def _hash_intent(intent: str) -> str:
    """Generate a short hash for skill deduplication."""
    return hashlib.sha256(intent.lower().strip().encode()).hexdigest()[:12]


def compress_skill(
    task_description: str,
    tool_calls: List[Dict[str, Any]],
    final_result: str,
    session_id: str = "",
    tags: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Compress a successful multi-step execution into a reusable skill.

    Args:
        task_description: The original user request / intent
        tool_calls: Ordered list of tool calls [{name, params, result}, ...]
        final_result: The final output text
        session_id: For provenance tracking
        tags: Optional categorization tags

    Returns:
        Skill filename if saved, None if task too simple to compress
    """
    # Don't compress trivial tasks (< 3 tool calls)
    if len(tool_calls) < 3:
        logger.debug("Task too simple to compress into skill (< 3 tool calls)")
        return None

    _ensure_dir()

    # Build the skill payload
    steps = []
    for i, call in enumerate(tool_calls):
        step = {
            "order": i + 1,
            "tool": call.get("name", "unknown"),
            "params_template": _templatize_params(call.get("params", {})),
            "expected_success": call.get("success", True),
        }
        # Capture error recovery if there was a failure then success
        if call.get("error_recovered"):
            step["recovery"] = {
                "error_pattern": call.get("error_pattern", ""),
                "fix_applied": call.get("fix_applied", ""),
            }
        steps.append(step)

    skill = {
        "version": "1.0",
        "created_at": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "trigger": {
            "intent": task_description,
            "intent_hash": _hash_intent(task_description),
            "keywords": _extract_keywords(task_description),
        },
        "steps": steps,
        "total_steps": len(steps),
        "expected_outcome": final_result[:500] if final_result else "",
        "tags": tags or _auto_tag(task_description),
        "replay_count": 0,
        "success_rate": 1.0,
    }

    # Save as JSON
    filename = f"skill_{skill['trigger']['intent_hash']}_{datetime.utcnow().strftime('%Y%m%d')}.json"
    filepath = os.path.join(SKILLS_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(skill, f, ensure_ascii=False, indent=2)
        logger.info(f"Skill compressed: {filename} ({len(steps)} steps)")
        return filename
    except Exception as e:
        logger.error(f"Failed to save skill: {e}")
        return None


def find_matching_skill(task_description: str) -> Optional[Dict[str, Any]]:
    """
    Search for a previously saved skill that matches the current task.

    Uses keyword overlap scoring to find the best match.
    Returns the skill payload if match confidence > 0.6, else None.
    """
    _ensure_dir()

    task_keywords = set(_extract_keywords(task_description))
    if not task_keywords:
        return None

    best_match = None
    best_score = 0.0

    try:
        for filename in os.listdir(SKILLS_DIR):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(SKILLS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    skill = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            skill_keywords = set(skill.get("trigger", {}).get("keywords", []))
            if not skill_keywords:
                continue

            # Jaccard similarity
            intersection = task_keywords & skill_keywords
            union = task_keywords | skill_keywords
            score = len(intersection) / len(union) if union else 0

            # Bonus for high success rate
            score *= skill.get("success_rate", 1.0)

            if score > best_score:
                best_score = score
                best_match = skill

    except FileNotFoundError:
        return None

    if best_score >= 0.6 and best_match:
        logger.info(
            f"Found matching skill: {best_match['trigger']['intent_hash']} "
            f"(confidence: {best_score:.2f})"
        )
        return best_match

    return None


def record_replay_outcome(intent_hash: str, success: bool):
    """
    Update a skill's success rate after replay.
    """
    _ensure_dir()

    try:
        for filename in os.listdir(SKILLS_DIR):
            if intent_hash in filename:
                filepath = os.path.join(SKILLS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    skill = json.load(f)

                skill["replay_count"] = skill.get("replay_count", 0) + 1
                total = skill["replay_count"]
                old_rate = skill.get("success_rate", 1.0)

                # Exponential moving average
                alpha = 0.3
                new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * old_rate
                skill["success_rate"] = round(new_rate, 3)

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(skill, f, ensure_ascii=False, indent=2)

                logger.info(
                    f"Skill {intent_hash} replay #{total}: "
                    f"{'success' if success else 'failure'} "
                    f"(rate: {skill['success_rate']})"
                )
                return
    except Exception as e:
        logger.warning(f"Failed to update skill replay: {e}")


def get_skill_prompt(skill: Dict[str, Any]) -> str:
    """
    Generate a prompt injection for the executor agent
    that teaches it how to replay a known skill.
    """
    steps_text = []
    for step in skill.get("steps", []):
        line = f"  Step {step['order']}: Use tool '{step['tool']}'"
        params = step.get("params_template", {})
        if params:
            line += f" with params: {json.dumps(params, ensure_ascii=False)}"
        if step.get("recovery"):
            line += (
                f"\n    ⚠️ If error '{step['recovery']['error_pattern']}' occurs, "
                f"apply fix: {step['recovery']['fix_applied']}"
            )
        steps_text.append(line)

    return (
        f"\n[SKILL REPLAY] A similar task was completed successfully before.\n"
        f"Original intent: {skill['trigger']['intent']}\n"
        f"Success rate: {skill.get('success_rate', 1.0):.0%}\n"
        f"Recommended steps:\n"
        + "\n".join(steps_text)
        + "\nFollow these steps closely, adapting parameters as needed.\n"
    )


def list_skills(limit: int = 20) -> List[Dict[str, Any]]:
    """List all saved skills with metadata."""
    _ensure_dir()
    skills = []

    try:
        for filename in sorted(os.listdir(SKILLS_DIR), reverse=True):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(SKILLS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    skill = json.load(f)
                skills.append({
                    "filename": filename,
                    "intent": skill.get("trigger", {}).get("intent", ""),
                    "steps": skill.get("total_steps", 0),
                    "replays": skill.get("replay_count", 0),
                    "success_rate": skill.get("success_rate", 1.0),
                    "tags": skill.get("tags", []),
                    "created": skill.get("created_at", ""),
                })
            except (json.JSONDecodeError, OSError):
                continue

            if len(skills) >= limit:
                break
    except FileNotFoundError:
        pass

    return skills


# ─── Private helpers ──────────────────────────────────────────

def _templatize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert concrete params to reusable templates.
    Replaces volatile values with placeholders.
    """
    template = {}
    for key, val in params.items():
        if isinstance(val, str):
            # Replace long file paths with template
            if "/" in val or "\\" in val:
                template[key] = "{{path}}"
            # Replace URLs
            elif val.startswith("http"):
                template[key] = "{{url}}"
            # Keep short values (actions, flags)
            elif len(val) < 50:
                template[key] = val
            else:
                template[key] = "{{content}}"
        else:
            template[key] = val
    return template


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from task description."""
    import re
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "and", "or", "not", "it", "this", "that", "but", "if",
        "как", "что", "это", "для", "на", "из", "по", "не", "да",
        "все", "мне", "мой", "его", "нужно", "можно", "ещё", "уже",
    }

    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{3,}\b', text.lower())
    return [w for w in words if w not in stop_words][:15]


def _auto_tag(text: str) -> List[str]:
    """Auto-generate tags from task description."""
    import re
    tags = []
    text_lower = text.lower()

    tag_patterns = {
        "code": r"(code|script|function|api|endpoint|class|module|напиш|создай код)",
        "research": r"(research|search|find|analyze|compare|report|исследуй|найди)",
        "presentation": r"(slide|deck|present|презент|слайд)",
        "file": r"(file|folder|directory|read|write|файл|папк)",
        "web": r"(website|scrape|crawl|browser|navigate|сайт|парс)",
        "deploy": r"(deploy|docker|build|install|server|развер|запуст)",
        "debug": r"(debug|fix|error|bug|broken|исправ|ошибк)",
        "data": r"(data|database|sql|csv|json|table|данн|база)",
    }

    for tag, pattern in tag_patterns.items():
        if re.search(pattern, text_lower):
            tags.append(tag)

    return tags or ["general"]
