"""
Dynamic Tool Selector — FIX-5.

Reduces tool context sent to the LLM from 40+ tools to a focused set of ≤12,
based on task classification. This dramatically improves tool-calling accuracy
on smaller models that get confused by too many tool definitions.

Essential tools (search, shell, file, message) are always included.
Task-specific tools are selected based on keyword matching.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Tools that are ALWAYS included regardless of task type
ESSENTIAL_TOOLS = {"search", "shell", "file", "message"}

# Task profiles: pattern → set of relevant tool names
TOOL_PROFILES = {
    "research": {
        "pattern": re.compile(
            r"(research|search|find|analyze|compare|summarize|report|news|"
            r"исследуй|найди|проанализируй|сравни|новости|отчёт)",
            re.IGNORECASE
        ),
        "tools": {"web_read", "parallel_search", "vector_search", "document"},
    },
    "coding": {
        "pattern": re.compile(
            r"(write|create|implement|code|function|class|api|debug|fix|refactor|test|"
            r"напиши|создай|код|функци|класс|исправь|тест|рефактор)",
            re.IGNORECASE
        ),
        "tools": {
            "python_repl", "fast_linter", "code_edit", "grep", "glob",
            "repo_map", "git", "patch", "ast_navigator", "swe_rag",
        },
    },
    "file_ops": {
        "pattern": re.compile(
            r"(file|read|write|edit|save|create file|delete|rename|directory|folder|"
            r"файл|прочитай|запиши|создай файл|удали|папк)",
            re.IGNORECASE
        ),
        "tools": {"grep", "glob", "code_edit", "git", "patch"},
    },
    "presentation": {
        "pattern": re.compile(
            r"(present|slide|deck|pitch|визуал|презентац|слайд)",
            re.IGNORECASE
        ),
        "tools": {"canvas", "vision", "image_gen"},
    },
    "media": {
        "pattern": re.compile(
            r"(image|video|audio|photo|picture|screenshot|render|"
            r"изображени|видео|аудио|фото|скриншот)",
            re.IGNORECASE
        ),
        "tools": {"image_gen", "video", "audio", "audio_synth", "vision", "media", "omnimodal"},
    },
    "devops": {
        "pattern": re.compile(
            r"(deploy|docker|container|server|monitor|log|infra|ci|cd|"
            r"деплой|контейнер|сервер|монитор|лог)",
            re.IGNORECASE
        ),
        "tools": {"deploy", "monitor", "infra", "log_analyzer", "expose"},
    },
    "browsing": {
        "pattern": re.compile(
            r"(browse|website|url|page|scrape|crawl|navigate|"
            r"сайт|страниц|браузер|скрапинг)",
            re.IGNORECASE
        ),
        "tools": {"browser", "vision_browser", "web_read"},
    },
}

# Maximum tools to send to LLM (including essential)
MAX_TOOLS = 12


def select_tools(
    task: str,
    all_tool_definitions: List[Dict[str, Any]],
    excluded_tools: List[str] = None,
) -> List[Dict[str, Any]]:
    """Select relevant tools for a task from all available tool definitions.
    
    Args:
        task: The natural language task description.
        all_tool_definitions: Full list of OpenAI-format tool definitions.
        excluded_tools: Tool names to exclude (e.g. from loop detection).
    
    Returns:
        Filtered list of tool definitions (max MAX_TOOLS).
    """
    if not task or not all_tool_definitions:
        return all_tool_definitions
    
    excluded = set(excluded_tools or [])
    
    # Build the set of desired tool names
    desired = set(ESSENTIAL_TOOLS)
    
    # Match task against profiles
    matched_profiles = []
    for profile_name, profile in TOOL_PROFILES.items():
        if profile["pattern"].search(task):
            desired.update(profile["tools"])
            matched_profiles.append(profile_name)
    
    # If no profile matched, include top coding tools as default
    if not matched_profiles:
        desired.update(TOOL_PROFILES["coding"]["tools"])
        matched_profiles.append("coding (default)")
    
    # Remove excluded tools
    desired -= excluded
    
    # Filter definitions
    selected = []
    for tool_def in all_tool_definitions:
        name = tool_def.get("function", {}).get("name", "")
        if name in excluded:
            continue
        if name in desired:
            selected.append(tool_def)
    
    # If we're over the limit, prioritize essential tools first
    if len(selected) > MAX_TOOLS:
        essential = [t for t in selected if t["function"]["name"] in ESSENTIAL_TOOLS]
        others = [t for t in selected if t["function"]["name"] not in ESSENTIAL_TOOLS]
        selected = essential + others[: MAX_TOOLS - len(essential)]
    
    if matched_profiles:
        logger.info(
            f"ToolSelector: {len(selected)}/{len(all_tool_definitions)} tools "
            f"for profiles: {', '.join(matched_profiles)}"
        )
    
    return selected
