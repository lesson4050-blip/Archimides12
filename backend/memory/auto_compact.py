"""
Auto-Compact Engine — Context Window Management.

Three compression levels:
- MICRO: Drop tool output details, keep summaries (saves ~30%)
- STANDARD: Summarize older conversation turns (saves ~60%)
- AGGRESSIVE: Keep only system + last N + summary (saves ~80%)
"""
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CompactLevel(str, Enum):
    NONE = "none"
    MICRO = "micro"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


@dataclass
class CompactConfig:
    """Configuration for auto-compact behavior."""
    max_context_tokens: int = 28000
    preserve_recent: int = 20
    micro_threshold: float = 0.6
    standard_threshold: float = 0.8
    aggressive_threshold: float = 0.95
    summary_max_tokens: int = 500
    preserve_tool_results: bool = True
    preserve_errors: bool = True


@dataclass
class CompactResult:
    """Result of a compaction operation."""
    level: CompactLevel
    original_count: int
    compacted_count: int
    original_tokens: int
    compacted_tokens: int
    summary: str = ""
    preserved_messages: List[int] = field(default_factory=list)


class AutoCompact:
    """Manages conversation context to fit within model limits via LLM summarization."""

    def __init__(self, config: Optional[CompactConfig] = None, router=None):
        self.config = config or CompactConfig()
        self.router = router
        self._compact_history: List[CompactResult] = []

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        total += len(str(part.get("text", ""))) // 4
            if msg.get("tool_calls"):
                total += len(msg["tool_calls"]) * 100
        return total

    def _get_compact_level(self, usage_ratio: float) -> CompactLevel:
        if usage_ratio >= self.config.aggressive_threshold:
            return CompactLevel.AGGRESSIVE
        elif usage_ratio >= self.config.standard_threshold:
            return CompactLevel.STANDARD
        elif usage_ratio >= self.config.micro_threshold:
            return CompactLevel.MICRO
        return CompactLevel.NONE

    def _find_referenced_tool_ids(self, recent_messages: List[Dict]) -> set:
        ids = set()
        for msg in recent_messages:
            if msg.get("role") == "tool":
                ids.add(msg.get("tool_call_id", ""))
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    ids.add(tc.get("id", ""))
        return ids

    def micro_compact(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            new_msg = msg.copy()
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 200:
                    new_msg["content"] = content[:200] + f"\n... [truncated {len(content) - 200} chars]"
            elif msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 500 and not msg.get("tool_calls"):
                    new_msg["content"] = content[:500] + "\n... [compacted]"
            result.append(new_msg)
        return result

    async def standard_compact(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        if len(messages) <= self.config.preserve_recent + 1:
            return messages, ""
        system_msgs = [m for m in messages[:3] if m.get("role") == "system"]
        recent_start = max(len(system_msgs), len(messages) - self.config.preserve_recent)
        old_msgs = messages[len(system_msgs):recent_start]
        recent_msgs = messages[recent_start:]
        referenced_ids = self._find_referenced_tool_ids(recent_msgs)
        summary = await self._summarize_messages(old_msgs)
        result = list(system_msgs)
        if summary:
            result.append({"role": "system", "content": f"[CONVERSATION SUMMARY]\n{summary}\n[END SUMMARY]"})
        if self.config.preserve_tool_results:
            for msg in old_msgs:
                if msg.get("role") == "tool" and msg.get("tool_call_id") in referenced_ids:
                    result.append(msg)
        if self.config.preserve_errors:
            for msg in old_msgs:
                content = str(msg.get("content", ""))
                if any(kw in content.lower() for kw in ["error", "exception", "traceback", "failed"]):
                    result.append(msg)
        result.extend(recent_msgs)
        return result, summary

    def aggressive_compact(self, messages: List[Dict[str, Any]], summary: str = "") -> List[Dict[str, Any]]:
        system_msgs = [m for m in messages[:3] if m.get("role") == "system"]
        recent = messages[-self.config.preserve_recent:]
        result = list(system_msgs)
        if summary:
            result.append({"role": "system", "content": f"[COMPACTED — previous {len(messages) - len(recent)} messages summarized]\n{summary}"})
        result.extend(recent)
        return result

    async def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        if not self.router:
            return self._extractive_summary(messages)
        conversation_text = ""
        for msg in messages[-30:]:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:300]
            conversation_text += f"[{role}]: {content}\n"
        try:
            resp = await self.router.generate(
                messages=[{"role": "user", "content": f"Summarize this conversation in 3-5 bullet points. Focus on: decisions made, errors encountered, files modified, current task status.\n\n{conversation_text}"}],
                task_hint="quick"
            )
            return resp.get("text", "")[:self.config.summary_max_tokens * 4]
        except Exception as e:
            logger.warning(f"LLM summary failed, using extractive: {e}")
            return self._extractive_summary(messages)

    def _extractive_summary(self, messages: List[Dict[str, Any]]) -> str:
        key_phrases = []
        for msg in messages:
            content = str(msg.get("content", ""))
            for line in content.split("\n"):
                if any(kw in line.lower() for kw in ["error", "created", "modified", "fixed", "added", "removed"]):
                    key_phrases.append(line.strip()[:100])
        seen = set()
        unique = []
        for p in key_phrases:
            h = hashlib.md5(p.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(p)
        return "\n".join(unique[:10])

    async def maybe_compact(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], CompactResult]:
        total_tokens = self.estimate_tokens(messages)
        usage_ratio = total_tokens / self.config.max_context_tokens
        level = self._get_compact_level(usage_ratio)
        if level == CompactLevel.NONE:
            return messages, CompactResult(level=CompactLevel.NONE, original_count=len(messages), compacted_count=len(messages), original_tokens=total_tokens, compacted_tokens=total_tokens)
        logger.info(f"Auto-compact triggered: level={level.value}, usage={usage_ratio:.1%}, tokens={total_tokens}")
        if level == CompactLevel.MICRO:
            compacted = self.micro_compact(messages)
            summary = ""
        elif level == CompactLevel.STANDARD:
            compacted, summary = await self.standard_compact(messages)
        else:
            _, summary = await self.standard_compact(messages) if self.router else (messages, self._extractive_summary(messages))
            compacted = self.aggressive_compact(messages, summary)
        new_tokens = self.estimate_tokens(compacted)
        result = CompactResult(level=level, original_count=len(messages), compacted_count=len(compacted), original_tokens=total_tokens, compacted_tokens=new_tokens, summary=summary)
        self._compact_history.append(result)
        logger.info(f"Compacted: {result.original_count} -> {result.compacted_count} msgs, {result.original_tokens} -> {result.compacted_tokens} tokens")
        return compacted, result
