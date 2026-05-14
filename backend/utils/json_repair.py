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
    Tries 7 strategies in order from most to least strict.
    """
    if not raw or not raw.strip():
        return None, "Empty input"

    strategies = [
        _try_direct_parse,
        _try_extract_json_block,
        _try_extract_first_object,
        _try_clean_trailing_commas,
        _try_complete_truncated,
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
            except (ValueError, SyntaxError, TypeError) as e:
                logging.getLogger(__name__).warning(f"JSON repair fallback error: {e}")
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


def _try_complete_truncated(raw: str) -> Tuple[Optional[Any], str]:
    """Complete truncated JSON by counting brackets."""
    start = raw.find('{')
    if start == -1:
        start = raw.find('[')
    if start == -1:
        return None, "No JSON start"

    candidate = raw[start:]

    def _try_close(s: str) -> Optional[Any]:
        """Try to close brackets/braces and parse."""
        # Close any unclosed string
        quote_count = s.count('"') - s.count('\\"')
        if quote_count % 2 != 0:
            s = s + '"'
        ob = s.count('{') - s.count('}')
        ab = s.count('[') - s.count(']')
        if ob <= 0 and ab <= 0:
            try:
                return json.loads(s)
            except Exception:
                return None
        closing = ']' * max(0, ab) + '}' * max(0, ob)
        try:
            return json.loads(s + closing)
        except Exception:
            return None

    # Strategy 1: close as-is
    result = _try_close(candidate)
    if result is not None:
        return result, ""

    # Strategy 2: strip from last comma and recompute
    last_comma = candidate.rfind(',')
    if last_comma > 0:
        stripped = candidate[:last_comma]
        result = _try_close(stripped)
        if result is not None:
            return result, ""

    # Strategy 3: strip from second-to-last comma
    if last_comma > 0:
        second_comma = candidate.rfind(',', 0, last_comma)
        if second_comma > 0:
            stripped2 = candidate[:second_comma]
            result = _try_close(stripped2)
            if result is not None:
                return result, ""

    return None, "Not truncated"


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
        except (ValueError, SyntaxError, TypeError) as e:
            logging.getLogger(__name__).warning(f"JSON repair fallback error: {e}")
    return None, "Aggressive extraction failed"
