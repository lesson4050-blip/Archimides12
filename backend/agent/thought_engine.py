"""
ThoughtEngine: Loads and caches the system prompt from YAML configuration.

Architecture decision: The system prompt is stored in prompts/system_prompt.yaml
instead of a raw Python string. This enables:
  - Version-controlled prompt changes via Git
  - A/B testing different prompt versions
  - Modification without touching Python code or restarting
  - Structured sections instead of one monolithic blob
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the YAML prompt config (relative to this module)
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT_PATH = _PROMPTS_DIR / "system_prompt.yaml"


class ThoughtEngine:
    _CACHED_SYSTEM_PROMPT: Optional[str] = None

    @classmethod
    def get_system_prompt(cls) -> str:
        if cls._CACHED_SYSTEM_PROMPT is None:
            cls._CACHED_SYSTEM_PROMPT = cls._build_system_prompt()
        return cls._CACHED_SYSTEM_PROMPT

    @classmethod
    def reload_prompt(cls) -> str:
        """Force reload the system prompt from YAML (useful for hot-reload)."""
        cls._CACHED_SYSTEM_PROMPT = None
        return cls.get_system_prompt()

    @staticmethod
    def _build_system_prompt() -> str:
        """Build the system prompt from YAML config file.
        
        Falls back to a minimal hardcoded prompt if YAML loading fails,
        ensuring the agent always has basic instructions.
        """
        try:
            import yaml
            
            if not _SYSTEM_PROMPT_PATH.exists():
                logger.warning(
                    f"System prompt YAML not found at {_SYSTEM_PROMPT_PATH}. "
                    f"Using minimal fallback prompt."
                )
                return ThoughtEngine._minimal_fallback()

            with open(_SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or not isinstance(config, dict):
                logger.error("System prompt YAML is empty or malformed")
                return ThoughtEngine._minimal_fallback()

            return ThoughtEngine._render_prompt(config)

        except ImportError:
            logger.warning("PyYAML not installed. Using minimal fallback prompt.")
            return ThoughtEngine._minimal_fallback()
        except (yaml.YAMLError, IOError) as e:
            logger.error(f"Failed to load system prompt YAML: {e}")
            return ThoughtEngine._minimal_fallback()

    @staticmethod
    def _render_prompt(config: dict) -> str:
        """Render a structured YAML config into a flat prompt string.
        
        Converts the hierarchical YAML structure into the linear text format
        that LLMs expect, preserving section headers for readability.
        """
        sections = []

        # ── Critical Rules ──
        if "critical_rules" in config:
            sections.append("CRITICAL RULES:")
            for rule in config["critical_rules"]:
                sections.append(f"- {rule}")

        # ── Identity ──
        identity = config.get("identity", {})
        if identity:
            sections.append(f"\nIDENTITY:")
            sections.append(f"- You are {identity.get('name', 'Archimedes')} — an {identity.get('role', 'autonomous agent')}.")
            if identity.get("sandbox_os"):
                sections.append(f"- You work inside an isolated {identity['sandbox_os']} Docker sandbox.")
            for rule in config.get("identity_rules", []):
                sections.append(f"- {rule}")

        # ── Agent Loop ──
        loop = config.get("agent_loop", {})
        if loop.get("steps"):
            sections.append("\nYOUR AGENT LOOP:")
            for i, step in enumerate(loop["steps"], 1):
                sections.append(f"{i}. {step}")

        # ── Mandatory Rules (grouped) ──
        mandatory = config.get("mandatory_rules", {})
        if mandatory:
            sections.append("\nMANDATORY RULES:")
            for group_name, rules in mandatory.items():
                if isinstance(rules, list):
                    for rule in rules:
                        sections.append(f"- {rule}")

        # ── Research Rules ──
        research = config.get("research_rules", {})
        if research:
            sections.append("\nRESEARCH RULES:")
            sections.append(f"- ALWAYS run minimum {research.get('min_search_queries', 3)} different search queries before writing.")
            if research.get("strategy"):
                sections.append(f"- {research['strategy']}")
            if research.get("year_in_queries"):
                sections.append("- When searching for benchmarks, always include the year in the query.")
            if not research.get("report_after_single_query", True):
                sections.append("- NEVER write a research report after only 1 search query — this is forbidden.")

        # ── Coding Rules ──
        coding = config.get("coding_rules", [])
        if coding:
            sections.append("\nELITE CODING RULES:")
            for rule in coding:
                sections.append(f"- {rule}")

        # ── SWE-Bench ──
        swe = config.get("swe_bench", {})
        if swe.get("steps"):
            sections.append("\nSWE-BENCH PROTOCOL:")
            for step in swe["steps"]:
                sections.append(f"- {step}")

        # ── Browser Rules ──
        browser = config.get("browser_rules", {})
        if browser:
            sections.append("\nBROWSER USAGE:")
            for key, value in browser.items():
                sections.append(f"- {key}: {value}")

        # ── Tool Catalog ──
        tools = config.get("tools", {})
        if tools:
            sections.append("\nTOOL SELECTION:")
            for name, desc in tools.items():
                sections.append(f"- {name}: {desc}")

        # ── Reasoning ──
        reasoning = config.get("reasoning", {})
        if reasoning:
            sections.append("\nREASONING ENGINE:")
            sections.append(f"Before EVERY tool call, engage your internal reasoning cycle:")
            for step in reasoning.get("cycle", []):
                sections.append(f"  {step}")
            if reasoning.get("format"):
                sections.append(f"Wrap reasoning in {reasoning['format']} tags.")
            if reasoning.get("on_failure"):
                sections.append(reasoning["on_failure"])

        prompt = "\n".join(sections)
        logger.debug(f"System prompt loaded from YAML: {len(prompt)} chars, {len(sections)} sections")
        return prompt

    @staticmethod
    def _minimal_fallback() -> str:
        """Minimal hardcoded prompt used when YAML loading fails."""
        return (
            "You are Archimedes — an autonomous ACTION agent.\n"
            "When given a task — DO IT IMMEDIATELY using tools.\n"
            "Your FIRST response must be a tool call, not text.\n"
            "Before every tool call, output a <thought>...</thought> block.\n"
            "WHEN COMPLETE: use message(type='result') with a detailed summary."
        )
