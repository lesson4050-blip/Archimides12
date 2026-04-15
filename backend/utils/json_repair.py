"""
JSON Repair & Validation Utility
Handles broken JSON from any LLM — small or large.
"""
import json
import re
import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def repair_and_parse(raw: str) -> Tuple[Optional[Any], str]:
    """
    Attempt to extract and parse JSON from raw LLM output.
    Returns (parsed_object, error_message).
    If successful, error_message is "".
    Tries 6 strategies in order from most to least strict.
    """
    if not raw or not raw.strip():
        return None, "Empty input"

    strategies = [
        _try_direct_parse,
        _try_extract_json_block,
        _try_extract_first_object,
        _try_clean_trailing_commas,
        _try_fix_single_quotes,
        _try_aggressive_extraction,
    ]

    for strategy in strategies:
        result, err = strategy(raw)
        if result is not None:
            return result, ""

    return None, f"All repair strategies failed. Raw: {raw[:300]}"


def _try_direct_parse(raw: str) -> Tuple[Optional[Any], str]:
    try:
        return json.loads(raw.strip()), ""
    except Exception as e:
        return None, str(e)


def _try_extract_json_block(raw: str) -> Tuple[Optional[Any], str]:
    """Extract from ```json ... ``` blocks"""
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*([\{\[].*?[\}\]])\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip()), ""
            except Exception:
                pass
    return None, "No JSON block found"


def _try_extract_first_object(raw: str) -> Tuple[Optional[Any], str]:
    """Find first complete { } or [ ] structure"""
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = raw.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(raw[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        candidate = raw[start:i+1]
                        try:
                            return json.loads(candidate), ""
                        except Exception:
                            break
    return None, "No complete object found"


def _try_clean_trailing_commas(raw: str) -> Tuple[Optional[Any], str]:
    """Remove trailing commas before ] or }"""
    start = raw.find('{')
    if start == -1:
        start = raw.find('[')
    if start == -1:
        return None, "No JSON start"
    end = max(raw.rfind('}'), raw.rfind(']')) + 1
    if end <= start:
        return None, "No JSON end"
    candidate = raw[start:end]
    cleaned = re.sub(r',\s*([\}\]])', r'\1', candidate)
    cleaned = re.sub(r'//[^\n]*\n', '\n', cleaned)
    try:
        return json.loads(cleaned), ""
    except Exception as e:
        return None, str(e)


def _try_fix_single_quotes(raw: str) -> Tuple[Optional[Any], str]:
    """Replace single quotes with double quotes (common LLM mistake)"""
    start = raw.find('{')
    if start == -1:
        return None, "No start"
    end = raw.rfind('}') + 1
    candidate = raw[start:end]
    try:
        # Only replace quotes that are clearly being used as JSON delimiters
        fixed = re.sub(r"(?<![\\])'", '"', candidate)
        return json.loads(fixed), ""
    except Exception as e:
        return None, str(e)


def _try_aggressive_extraction(raw: str) -> Tuple[Optional[Any], str]:
    """Last resort: find any key:value patterns and reconstruct"""
    # Look for tool_call pattern specifically
    tc_match = re.search(
        r'"?tool_call"?\s*:\s*\{[^}]+\}', raw, re.DOTALL
    )
    if tc_match:
        try:
            wrapper = '{' + tc_match.group(0) + '}'
            return json.loads(wrapper), ""
        except Exception:
            pass
    return None, "Aggressive extraction failed"
