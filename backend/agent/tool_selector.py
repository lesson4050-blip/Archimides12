"""
Dynamic Tool Selector — FIX-5.

Reduces tool context sent to the LLM from 40+ tools to a focused set of <=12,
based on task classification. This dramatically improves tool-calling accuracy
on smaller models that get confused by too many tool definitions.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Task profiles mapping directly to tools list
TOOL_PROFILES = {
    "research": ["search", "web_read"],
    "conversation": ["search", "web_read"],
    "default": ["search", "shell", "file", "web_read"],
    "coding": ["python_repl", "fast_linter", "code_edit", "grep", "glob", "repo_map", "git", "patch", "ast_navigator", "swe_rag", "shell", "file", "search"],
    "file_ops": ["grep", "glob", "code_edit", "git", "patch", "shell", "file"],
    "presentation": ["marp", "canvas", "canvas_engine", "vision", "image_gen"],
    "media": ["image_gen", "video", "audio", "audio_synth", "vision", "media", "omnimodal"],
    "devops": ["deploy", "monitor", "infra", "log_analyzer", "expose", "shell", "file"],
    "browsing": ["browser", "vision_browser", "web_read"]
}

TASK_CLASSIFIERS = {
    "research": re.compile(
        r'\b(найди|поищи|search|find|news|новости|latest|what is|who is|расскажи|покажи)\b',
        re.IGNORECASE
    ),
    "conversation": re.compile(
        r"^(привет|здравствуй|хай|hi|hello|hey|добрый\s+(день|вечер|утро)|как\s+дела|помо(щь|ги))[\s!.?]*$",
        re.IGNORECASE
    ),
    "coding": re.compile(
        r"(write|create|implement|code|function|class|api|debug|fix|refactor|test|"
        r"напиши|создай|код|функци|класс|исправь|тест|рефактор)",
        re.IGNORECASE
    ),
    "file_ops": re.compile(
        r"(file|read|write|edit|save|create file|delete|rename|directory|folder|"
        r"файл|прочитай|запиши|создай файл|удали|папк)",
        re.IGNORECASE
    ),
    "presentation": re.compile(
        r"(present|slide|deck|pitch|визуал|презентац|слайд)",
        re.IGNORECASE
    ),
    "media": re.compile(
        r"(image|video|audio|photo|picture|screenshot|render|"
        r"изображени|видео|аудио|фото|скриншот)",
        re.IGNORECASE
    ),
    "devops": re.compile(
        r"(deploy|docker|container|server|monitor|log|infra|ci|cd|"
        r"деплой|контейнер|сервер|монитор|лог)",
        re.IGNORECASE
    ),
    "browsing": re.compile(
        r"(browse|website|url|page|scrape|crawl|navigate|"
        r"сайт|страниц|браузер|скрапинг)",
        re.IGNORECASE
    )
}

MAX_TOOLS = 12

# Essential tools that must always be available to the agent for recovery and operations
ESSENTIAL_TOOLS = {"search", "shell", "file"}

def select_tools(
    task: str,
    all_tool_definitions: List[Dict[str, Any]],
    excluded_tools: List[str] = None,
    max_tools: int = MAX_TOOLS
) -> List[Dict[str, Any]]:
    """Select relevant tools for a task from all available tool definitions.
    
    Args:
        task: The natural language task description.
        all_tool_definitions: Full list of OpenAI-format tool definitions.
        excluded_tools: Tool names to exclude (e.g. from loop detection).
    
    Returns:
        Filtered list of tool definitions.
    """
    if not task or not all_tool_definitions:
        return all_tool_definitions
    
    excluded = set(excluded_tools or [])
    
    matched_profile = "default"
    for profile_name, pattern in TASK_CLASSIFIERS.items():
        if pattern.search(task):
            matched_profile = profile_name
            break
            
    desired = set(TOOL_PROFILES.get(matched_profile, TOOL_PROFILES["default"]))
    desired.update(ESSENTIAL_TOOLS)
    desired -= excluded
    
    selected = []
    for tool_def in all_tool_definitions:
        name = tool_def.get("function", {}).get("name", "")
        if name in excluded:
            continue
        if name in desired:
            selected.append(tool_def)
    
    if len(selected) > max_tools:
        selected = selected[:max_tools]
    
    logger.info(f"ToolSelector: {len(selected)} tools for profile: {matched_profile}")
    return selected
