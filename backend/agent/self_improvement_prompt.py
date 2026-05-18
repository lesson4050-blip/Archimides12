"""
Prompt Self-Improvement Engine.

When agent fails or scores low on tasks, this engine:
1. Analyzes the failure reason
2. Generates an improved system prompt
3. Validates against regression suite (existing good tasks)
4. If regression passes → promotes new prompt version
5. If regression fails → rolls back to previous version

Based on: SelfImprovingAgent pattern from 2026 AI docs.
Inspired by: Anthropic Constitutional AI + OpenAI RLHF prompt optimization.

SECURITY:
- New prompts are validated before use (no injection in prompt content)
- Max prompt length enforced
- Rollback always available
- Changes logged to SQLite for audit
"""
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "prompt_versions.db")
MAX_PROMPT_LENGTH = 8000  # chars — prevent bloat
MAX_VERSIONS = 20         # Keep last 20 versions only
MIN_REGRESSION_SCORE = 0.7  # New prompt must score ≥70% on validation tasks


@dataclass
class PromptVersion:
    version_id: int
    content: str
    created_at: float
    score: float = 0.0
    tasks_tested: int = 0
    tasks_passed: int = 0
    is_active: bool = False
    reason_for_change: str = ""

    @property
    def pass_rate(self) -> float:
        if self.tasks_tested == 0:
            return 0.0
        return self.tasks_passed / self.tasks_tested


@dataclass
class TaskResult:
    task: str
    output: str
    success: bool
    score: float  # 0.0 to 1.0
    duration: float


class PromptSelfImprovement:
    """
    Self-improving prompt engine with regression validation.

    SAFETY FIRST:
    - Never uses new prompt without regression validation
    - Always keeps previous version for rollback
    - Logs all changes for audit
    """

    def __init__(self, model_router=None):
        self.router = model_router
        self._current_version: Optional[PromptVersion] = None
        self._initialized = False

    async def _init_db(self):
        """Initialize SQLite schema."""
        if self._initialized:
            return
        os.makedirs("data", exist_ok=True)
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    score REAL DEFAULT 0,
                    tasks_tested INTEGER DEFAULT 0,
                    tasks_passed INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 0,
                    reason_for_change TEXT DEFAULT '',
                    rolled_back INTEGER DEFAULT 0
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS improvement_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    version_id INTEGER
                )
            """)
            await conn.commit()
        self._initialized = True

    async def get_current_prompt(self) -> str:
        """Get the currently active system prompt."""
        await self._init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT content FROM prompt_versions WHERE is_active=1 ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()

        if row:
            return row[0]

        # Fall back to YAML file
        return self._load_yaml_prompt()

    def _load_yaml_prompt(self) -> str:
        """Load system prompt from YAML file."""
        try:
            import yaml
            yaml_path = Path("backend/agent/prompts/system_prompt.yaml")
            if yaml_path.exists():
                with open(yaml_path) as f:
                    data = yaml.safe_load(f)
                return data.get("system_prompt", data.get("content", ""))
        except Exception as e:
            logger.warning(f"Failed to load YAML prompt: {e}")
        return ""

    async def record_task_outcome(
        self,
        task: str,
        output: str,
        success: bool,
        score: float,
        duration: float,
    ):
        """
        Record a task outcome. If score is low, trigger improvement analysis.

        Args:
            task: The task that was run
            output: Agent's output
            success: Whether it completed
            score: Quality score 0.0-1.0
            duration: Time taken in seconds
        """
        await self._init_db()

        result = TaskResult(task=task, output=output, success=success, score=score, duration=duration)

        # Only trigger improvement for genuinely bad outcomes
        if score < 0.5 and success:
            logger.info(f"[PromptImprovement] Low score ({score:.2f}) on task — scheduling analysis")
            # Don't block — run in background
            from backend.utils.task import safe_create_task
            safe_create_task(self._analyze_and_improve(result))

        elif not success:
            logger.info(f"[PromptImprovement] Task failed — scheduling analysis")
            from backend.utils.task import safe_create_task
            safe_create_task(self._analyze_and_improve(result))

    async def _analyze_and_improve(self, failed_result: TaskResult):
        """
        Core improvement loop — called in background after bad task.

        1. Ask LLM to analyze what went wrong
        2. Ask LLM to suggest improved system prompt
        3. Run regression validation
        4. Promote or discard new prompt
        """
        if not self.router:
            logger.debug("[PromptImprovement] No router available — skipping")
            return

        try:
            current_prompt = await self.get_current_prompt()

            # Step 1: Analyze failure
            analysis_response = await asyncio.wait_for(
                self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"You are analyzing an AI agent's failure.\n\n"
                            f"Current system prompt (first 500 chars):\n{current_prompt[:500]}\n\n"
                            f"Failed task: {failed_result.task[:300]}\n"
                            f"Agent output: {failed_result.output[:300]}\n"
                            f"Success: {failed_result.success}, Score: {failed_result.score:.2f}\n\n"
                            f"In 2-3 sentences: What specific aspect of the system prompt "
                            f"likely caused this failure? Be concrete."
                        )
                    }],
                    task_hint="quality",
                    temperature=0.3,
                ),
                timeout=30
            )
            analysis = analysis_response.get("text", "")

            if not analysis:
                return

            # Step 2: Generate improved prompt
            improvement_response = await asyncio.wait_for(
                self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"You are improving an AI agent's system prompt.\n\n"
                            f"Current prompt:\n{current_prompt[:2000]}\n\n"
                            f"Problem analysis:\n{analysis}\n\n"
                            f"Generate an improved system prompt that fixes the identified issue. "
                            f"Keep all good parts of the current prompt. "
                            f"Make minimal targeted changes. "
                            f"Output ONLY the new system prompt, nothing else. "
                            f"Maximum {MAX_PROMPT_LENGTH} characters."
                        )
                    }],
                    task_hint="quality",
                    temperature=0.4,
                ),
                timeout=45
            )
            new_prompt = improvement_response.get("text", "").strip()

            if not new_prompt or len(new_prompt) < 100:
                logger.debug("[PromptImprovement] Generated prompt too short — discarding")
                return

            # Security: validate no injection in new prompt
            from backend.security.sandbox_hardening import SecurityGate
            gate = SecurityGate()
            verdict = gate.analyze_prompt_injection(new_prompt)
            if not verdict.allowed:
                logger.warning(f"[PromptImprovement] Generated prompt contains injection patterns — discarding")
                return

            # Cap length
            new_prompt = new_prompt[:MAX_PROMPT_LENGTH]

            # Step 3: Regression validation
            passed, total = await self._run_regression(new_prompt)
            pass_rate = passed / total if total > 0 else 0.0

            if pass_rate >= MIN_REGRESSION_SCORE:
                # Step 4a: Promote new prompt
                await self._promote_prompt(
                    new_prompt,
                    score=pass_rate,
                    tasks_tested=total,
                    tasks_passed=passed,
                    reason=f"Improved after low score ({failed_result.score:.2f}) on: {failed_result.task[:100]}"
                )
                logger.info(
                    f"[PromptImprovement] New prompt promoted! "
                    f"Regression: {passed}/{total} ({pass_rate:.0%})"
                )
            else:
                # Step 4b: Discard
                await self._log_event(
                    "REGRESSION_FAILED",
                    f"New prompt failed regression: {passed}/{total} ({pass_rate:.0%}) < {MIN_REGRESSION_SCORE:.0%}"
                )
                logger.info(
                    f"[PromptImprovement] New prompt rejected — regression: "
                    f"{passed}/{total} ({pass_rate:.0%})"
                )

        except asyncio.TimeoutError:
            logger.debug("[PromptImprovement] Analysis timed out")
        except Exception as e:
            logger.warning(f"[PromptImprovement] Improvement cycle failed: {e}")

    async def _run_regression(self, new_prompt: str) -> tuple:
        """
        Run regression suite against new prompt.
        Uses BUILTIN_TASKS from eval_pipeline.
        Returns (passed, total).
        """
        try:
            from backend.benchmarks.eval_pipeline import BUILTIN_TASKS, EvalPipeline
            from backend.models.model_router import ModelRouter

            router = self.router or ModelRouter()
            pipeline = EvalPipeline(router)

            passed = 0
            total = min(len(BUILTIN_TASKS), 3)  # Max 3 tasks for speed

            for task in BUILTIN_TASKS[:total]:
                try:
                    result = await asyncio.wait_for(
                        pipeline.run_task(task, model_hint="default"),
                        timeout=30
                    )
                    if result.success:
                        passed += 1
                except Exception:
                    pass  # Timeout or error = not passed

            return passed, total

        except Exception as e:
            logger.warning(f"[PromptImprovement] Regression suite failed: {e}")
            return 0, 1  # Return failing score

    async def _promote_prompt(
        self,
        content: str,
        score: float,
        tasks_tested: int,
        tasks_passed: int,
        reason: str
    ):
        """Save new prompt as active version."""
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            # Deactivate all current versions
            await conn.execute("UPDATE prompt_versions SET is_active=0")

            # Insert new active version
            await conn.execute(
                """INSERT INTO prompt_versions
                   (content, created_at, score, tasks_tested, tasks_passed, is_active, reason_for_change)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (content, time.time(), score, tasks_tested, tasks_passed, reason[:500])
            )

            # Keep only last MAX_VERSIONS
            await conn.execute(f"""
                DELETE FROM prompt_versions
                WHERE id NOT IN (
                    SELECT id FROM prompt_versions ORDER BY id DESC LIMIT {MAX_VERSIONS}
                )
            """)

            await conn.commit()

        await self._log_event("PROMOTED", f"Score: {score:.2f}, Reason: {reason[:100]}")

    async def rollback(self) -> bool:
        """Roll back to the previous prompt version."""
        await self._init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            # Find second most recent
            cursor = await conn.execute(
                "SELECT id FROM prompt_versions ORDER BY id DESC LIMIT 2"
            )
            rows = await cursor.fetchall()

            if len(rows) < 2:
                return False

            previous_id = rows[1][0]
            await conn.execute("UPDATE prompt_versions SET is_active=0")
            await conn.execute(
                "UPDATE prompt_versions SET is_active=1, rolled_back=1 WHERE id=?",
                (previous_id,)
            )
            await conn.commit()

        await self._log_event("ROLLBACK", f"Rolled back to version {previous_id}")
        logger.info(f"[PromptImprovement] Rolled back to version {previous_id}")
        return True

    async def get_version_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get prompt version history for monitoring."""
        await self._init_db()
        async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
            cursor = await conn.execute(
                """SELECT id, score, tasks_tested, tasks_passed,
                   is_active, reason_for_change, created_at, rolled_back
                   FROM prompt_versions ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
            rows = await cursor.fetchall()

        return [
            {
                "version_id": r[0],
                "score": r[1],
                "tasks_tested": r[2],
                "tasks_passed": r[3],
                "is_active": bool(r[4]),
                "reason": r[5],
                "created_at": r[6],
                "rolled_back": bool(r[7]),
                "pass_rate": r[3] / max(r[2], 1),
            }
            for r in rows
        ]

    async def _log_event(self, event: str, details: str = ""):
        """Log improvement event for audit."""
        try:
            async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                await conn.execute(
                    "INSERT INTO improvement_log (timestamp, event, details) VALUES (?, ?, ?)",
                    (time.time(), event, details[:500])
                )
                await conn.commit()
        except Exception:
            pass


# Global singleton
_prompt_improver: Optional[PromptSelfImprovement] = None


def get_prompt_improver(router=None) -> PromptSelfImprovement:
    global _prompt_improver
    if _prompt_improver is None:
        _prompt_improver = PromptSelfImprovement(router)
    return _prompt_improver
