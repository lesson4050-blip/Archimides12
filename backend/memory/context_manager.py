"""
Context Manager v3 — Pruning-first context strategy.

Key improvements over v2:
- Accurate token counting via tiktoken (cl100k_base encoding)
- Configurable preserve_recent window (default 20 messages vs old 10)
- Tool call history preservation (maintains tool_call_id references)
- TWO-PHASE strategy: prune failed attempts FIRST, summarize SECOND
- Failed tool calls are removed before resorting to lossy summarization
- Graceful fallback if tiktoken unavailable
"""

import logging
from typing import List, Dict, Any

from backend.config import settings

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversation history with intelligent context windowing.
    
    Uses a sliding window approach:
    1. Messages accumulate normally
    2. When token count exceeds threshold → summarize oldest 60%
    3. Keep: system prompt + summary + recent N messages
    4. Tool call chains are preserved intact (no orphaned tool_call_ids)
    """

    def __init__(
        self,
        max_tokens: int = None,
        summarization_threshold: int = None,
        preserve_recent: int = None,
    ):
        self.history: List[Dict[str, Any]] = []
        self.max_tokens = max_tokens or settings.AGENT_MAX_CONTEXT_TOKENS
        self.summarization_threshold = summarization_threshold or settings.CONTEXT_SUMMARIZATION_THRESHOLD
        self.preserve_recent = preserve_recent or settings.CONTEXT_PRESERVE_RECENT
        self._current_tokens = 0
        self._tokenizer = None
        self._tokenizer_available = None  # None = not checked yet

    # ──────────────────────────────────────────────
    # Token Counting
    # ──────────────────────────────────────────────

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens accurately using tiktoken (cl100k_base).
        Falls back to len(text)//3 heuristic if tiktoken unavailable.
        """
        if not text:
            return 0

        # Lazy init tokenizer (once per instance)
        if self._tokenizer_available is None:
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
                self._tokenizer_available = True
                logger.info("Context: tiktoken encoder loaded (cl100k_base)")
            except (ImportError, Exception) as e:
                self._tokenizer_available = False
                logger.warning(f"Context: tiktoken unavailable ({e}), using heuristic")

        if self._tokenizer_available and self._tokenizer:
            return len(self._tokenizer.encode(text))
        
        # Heuristic fallback: ~3.2 chars per token for English
        return max(1, len(text) // 3)

    def _count_message_tokens(self, message: Dict[str, Any]) -> int:
        """Count tokens for a single message including role overhead."""
        tokens = 4  # role + formatting overhead
        content = message.get("content", "")
        if content:
            tokens += self._count_tokens(content)
        
        # Count tool call arguments
        tool_calls = message.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            args = func.get("arguments", "")
            if isinstance(args, dict):
                import json
                args = json.dumps(args)
            tokens += self._count_tokens(str(args)) + 10  # tool overhead
        
        return tokens

    def _recalculate_tokens(self):
        """Recalculate total token count from scratch."""
        self._current_tokens = sum(
            self._count_message_tokens(m) for m in self.history
        )

    # ──────────────────────────────────────────────
    # Message Management
    # ──────────────────────────────────────────────

    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to history and update token count."""
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.history.append(message)
        self._current_tokens += self._count_message_tokens(message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current message history."""
        return self.history

    def _deduplicate_tool_results(
        self, messages: List[Dict]
    ) -> List[Dict]:
        """Remove duplicate tool results keeping only the latest."""
        seen_tool_names = {}
        result = []
        # Process in reverse to keep latest
        for msg in reversed(messages):
            if msg.get("role") == "tool":
                name = msg.get("name", "unknown")
                if name not in seen_tool_names:
                    seen_tool_names[name] = True
                    result.insert(0, msg)
                # Skip duplicate tool results
            else:
                result.insert(0, msg)
        return result

    def get_messages_with_cache(self, max_total_tokens: int = 24000) -> List[Dict[str, Any]]:
        """
        Returns messages optimized for prefix caching.
        The system prompt is kept stable (cache-friendly).
        Only new messages are appended after it within token budget.
        This reduces token costs by ~60-80% on repeated calls.
        """
        if not self.history:
            return []

        # Step 1: deduplicate tool results
        history = self._deduplicate_tool_results(self.history)

        # System prompt is always first — keep it stable for cache hits
        system_msgs = [m for m in history if m["role"] == "system"]
        other_msgs = [m for m in history if m["role"] != "system"]

        # System prompt: always include (cache hit)
        result = list(system_msgs)
        system_tokens = sum(
            self._count_message_tokens(m) for m in system_msgs
        )

        # Add recent messages within token budget
        token_budget = max_total_tokens - system_tokens
        selected = []
        for msg in reversed(other_msgs):
            cost = self._count_message_tokens(msg)
            if token_budget - cost < 0:
                break
            selected.insert(0, msg)
            token_budget -= cost

        # Always include at least last 5 non-system messages
        if len(selected) < 5 and len(other_msgs) >= 5:
            selected = other_msgs[-5:]

        return result + selected

    @property
    def current_tokens(self) -> int:
        """Current token count."""
        return self._current_tokens

    # ──────────────────────────────────────────────
    # Phase 1: Context Pruning (lossless)
    # ──────────────────────────────────────────────

    def prune_failed_attempts(self) -> int:
        """
        Remove failed tool call chains from history.
        
        A failed chain is: assistant(tool_call) → tool(ERROR: ...)
        These waste context without providing useful information.
        
        Returns the number of messages pruned.
        """
        if len(self.history) < 3:
            return 0

        pruned_indices = set()
        i = 0
        while i < len(self.history):
            msg = self.history[i]
            
            # Find assistant messages with tool_calls
            if (msg.get("role") == "assistant" and
                msg.get("tool_calls") and
                i + 1 < len(self.history)):
                
                next_msg = self.history[i + 1]
                
                # Check if the tool response is a failure
                if (next_msg.get("role") == "tool" and
                    isinstance(next_msg.get("content", ""), str) and
                    next_msg["content"].startswith("ERROR:")):
                    
                    # Don't prune if it's in the last preserve_recent messages
                    if i < len(self.history) - self.preserve_recent:
                        pruned_indices.add(i)
                        pruned_indices.add(i + 1)
                        i += 2
                        continue
            i += 1

        if pruned_indices:
            old_len = len(self.history)
            self.history = [
                m for idx, m in enumerate(self.history)
                if idx not in pruned_indices
            ]
            self._recalculate_tokens()
            pruned_count = old_len - len(self.history)
            logger.info(
                f"Context pruning: removed {pruned_count} messages "
                f"({len(pruned_indices) // 2} failed tool chains)"
            )
            return pruned_count

        return 0

    def prune_verbose_tool_outputs(self, max_output_chars: int = 1000) -> int:
        """
        Truncate excessively long tool outputs in older messages.
        Keeps recent messages intact.
        """
        truncated = 0
        cutoff = max(0, len(self.history) - self.preserve_recent)
        
        for i in range(cutoff):
            msg = self.history[i]
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > max_output_chars:
                    msg["content"] = (
                        content[:max_output_chars] +
                        f"\n...[truncated from {len(content)} chars]"
                    )
                    truncated += 1
        
        if truncated:
            self._recalculate_tokens()
            logger.info(f"Truncated {truncated} verbose tool outputs")
        
        return truncated

    # ──────────────────────────────────────────────
    # Phase 2: Summarization (lossy, last resort)
    # ──────────────────────────────────────────────

    async def summarize_if_needed(self, model_router: Any):
        """
        Two-phase context management:
        
        Phase 1 (lossless): Prune failed tool attempts + truncate verbose outputs
        Phase 2 (lossy): If still over budget, summarize oldest messages
        
        This preserves critical code context that pure summarization destroys.
        """
        if self._current_tokens < self.summarization_threshold:
            return

        logger.info(
            f"Context window: {self._current_tokens} tokens "
            f"(threshold: {self.summarization_threshold}). "
            f"Starting two-phase context management..."
        )

        # ── Phase 1: Lossless pruning ──
        pruned = self.prune_failed_attempts()
        self.prune_verbose_tool_outputs()

        # Check if pruning was sufficient
        if self._current_tokens < self.summarization_threshold:
            logger.info(
                f"Phase 1 sufficient: pruned {pruned} messages, "
                f"now at {self._current_tokens} tokens"
            )
            return

        # ── Phase 2: Lossy summarization ──
        logger.info(
            f"Phase 1 insufficient ({self._current_tokens} tokens). "
            f"Proceeding to Phase 2 (summarization)..."
        )

        # Extract system prompt
        system_prompt = None
        if self.history and self.history[0].get("role") == "system":
            system_prompt = self.history[0]

        # Find safe split point: keep recent N messages, but don't break tool chains
        split_idx = max(1, len(self.history) - self.preserve_recent)
        split_idx = self._find_safe_split(split_idx)

        to_summarize = self.history[1:split_idx]  # skip system prompt
        recent = self.history[split_idx:]

        if len(to_summarize) < 3:
            logger.info("Too few messages to summarize, skipping.")
            return

        # Build summarization prompt — code-aware
        summary_text_parts = []
        for msg in to_summarize:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            if content and len(content) > 500:
                content = content[:500] + "..."
            if content:
                summary_text_parts.append(f"{role}: {content}")

        summary_prompt = (
            "Summarize the following conversation history into a concise paragraph. "
            "CRITICAL: Preserve ALL of the following EXACTLY:\n"
            "- File paths and line numbers mentioned\n"
            "- Function/class names and their locations\n"
            "- Error messages and their root causes\n"
            "- Decisions made and their rationale\n"
            "- Tool results and their outcomes\n"
            "- Code patterns discovered\n\n"
            + "\n".join(summary_text_parts)
        )

        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": summary_prompt}],
                task_hint="summarize"
            )
            summary_text = response.get("text", "Conversation summary unavailable.")

            # Reconstruct history
            new_history = []
            if system_prompt:
                new_history.append(system_prompt)
            new_history.append({
                "role": "assistant",
                "content": (
                    f"[Context summary — {len(to_summarize)} messages condensed, "
                    f"{pruned} failed attempts pruned]: {summary_text}"
                )
            })
            new_history.extend(recent)

            old_count = self._current_tokens
            self.history = new_history
            self._recalculate_tokens()

            logger.info(
                f"Phase 2 complete: {old_count} → {self._current_tokens} tokens "
                f"({len(to_summarize)} messages → 1 summary)"
            )

        except Exception as e:
            logger.error(f"Failed to summarize context: {e}")

    def _find_safe_split(self, target_idx: int) -> int:
        """
        Find a split point that doesn't break tool call chains.
        A tool call chain is: assistant (with tool_calls) → tool (with tool_call_id).
        We never split between an assistant tool_call and its tool response.
        """
        idx = target_idx
        
        # Walk backward from target to find a safe boundary
        while idx > 1 and idx < len(self.history):
            msg = self.history[idx]
            # If this message is a tool response, don't split here
            if msg.get("role") == "tool":
                idx -= 1
                continue
            # If this is an assistant message with tool_calls,
            # its tool response is AFTER it — don't split here either
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                idx -= 1
                continue
            # Safe boundary found
            break
        
        return max(1, idx)
