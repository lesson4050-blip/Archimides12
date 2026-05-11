"""
Skill Library — когнитивное сжатие опыта.
Если агент однажды решил задачу хорошо,
он запоминает «как» и переиспользует.

Top-level implementation:
- Bag-of-Words hashing (order-invariant)
- Jaccard similarity fuzzy matching (45% threshold)
- Use-count tracking + last_used timestamp
- TTL-based eviction (30 days unused)
- Thread-safe I/O with file locking
- Quality gating (>= 0.7)
"""
import json
import hashlib
import logging
import re
import string
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SKILL_DIR = Path("data/skills")
_SKILL_TTL_DAYS = 30  # Evict skills unused for 30+ days
_MAX_SKILLS = 200  # Hard cap on stored skills


class SkillLibrary:
    """
    Cognitive Experience Library for Archimedes.
    
    This class manages the lifecycle of 'skills' — successful task-solving trajectories
    that can be reused for similar future requests. It uses a combination of 
    exact Bag-of-Words hashing and fuzzy Jaccard similarity for retrieval.
    
    Attributes:
        storage (Path): Root directory for skill storage.
        _index (Dict): Metadata index for all stored skills.
        _lock (threading.Lock): Ensures thread-safety for I/O operations.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initializes the skill library and loads the existing index.
        
        Args:
            storage_dir (str, optional): Custom path for skill storage. Defaults to SKILL_DIR.
        """
        self.storage: Path = Path(storage_dir or SKILL_DIR)
        self.storage.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, Dict[str, Any]] = {}
        self._lock: threading.Lock = threading.Lock()
        self._load_index()

    def _load_index(self) -> None:
        """Loads the skill index from the storage directory. If corrupted, starts with an empty index."""
        idx_file = self.storage / "index.json"
        if idx_file.exists():
            try:
                self._index = json.loads(idx_file.read_text("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.warning("Skill index corrupted, starting fresh")
                self._index = {}
        logger.info(f"SkillLibrary loaded: {len(self._index)} skills")

    def _save_index(self) -> None:
        """Persists the current skill index to disk using atomic file write and thread locking."""
        idx_file = self.storage / "index.json"
        with self._lock:
            idx_file.write_text(
                json.dumps(self._index, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    def _task_signature(self, task_description: str) -> str:
        """
        Generates a robust, order-invariant signature for a task.
        
        Uses a Bag-of-Words (BoW) approach:
        1. Lowercases and strips punctuation.
        2. Tokenizes and removes short stop-words.
        3. Sorts unique words alphabetically.
        4. MD5 hashes the result.
        
        Args:
            task_description (str): Natural language task description.
            
        Returns:
            str: A 12-character MD5 hex signature.
        """
        text = task_description.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))

        # Tokenize, remove stop words (len <= 2), sort alphabetically
        words = sorted(set(w for w in text.split() if len(w) > 2))

        normalized = " ".join(words)[:500]
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def find_skill(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Finds a matching skill using exact signature or fuzzy token matching.
        
        Retreival logic:
        1. Exact hash match (fastest).
        2. Jaccard similarity fuzzy match (score >= 0.45).
        
        Args:
            task (str): The new task description to match against.
            
        Returns:
            Dict, optional: The skill data with hit metadata, or None if no match found.
        """
        sig = self._task_signature(task)

        # Exact match (fast path)
        if sig in self._index:
            skill = self._load_skill_file(sig)
            if skill:
                self._record_hit(sig)
                skill["_hit"] = True
                skill["_fuzzy"] = False
                logger.info(f"Skill EXACT HIT: {sig} ({skill.get('label','')})")
                return skill

        # Jaccard fuzzy match (slow path)
        task_words = self._tokenize(task)
        if not task_words:
            return None

        best_match = None
        best_score = 0.0

        for sig_key, meta in self._index.items():
            # Compare against stored task text, not just label
            # Load task from index meta if available, else fall back to label
            candidate_text = meta.get('task', '') or meta.get('label', '')
            label_words = self._tokenize(candidate_text)

            if not label_words:
                continue

            intersection = len(task_words & label_words)
            union = len(task_words | label_words)
            score = intersection / union if union > 0 else 0

            if score > 0.45 and score > best_score:
                best_score = score
                best_match = sig_key

        if best_match:
            skill = self._load_skill_file(best_match)
            if skill:
                self._record_hit(best_match)
                skill["_hit"] = True
                skill["_fuzzy"] = True
                skill["_similarity"] = round(best_score, 2)
                logger.info(
                    f"Skill FUZZY HIT: {best_match} "
                    f"(sim={best_score:.2f}, label={self._index[best_match].get('label','')})"
                )
                return skill

        return None

    def store_skill(
        self,
        task: str,
        trajectory: List[Dict[str, Any]],
        label: Optional[str] = None,
        quality_score: float = 1.0,
    ) -> None:
        """
        Compresses and stores a successful task trajectory.
        
        Only stores if the quality_score meets the threshold (>= 0.7).
        Automatically evicts older/lower-quality skills if library capacity is reached.
        
        Args:
            task (str): The original task description.
            trajectory (List[Dict]): The sequence of tool calls and results.
            label (str, optional): A short name for the skill.
            quality_score (float): Self-evaluated quality (0.0 to 1.0).
        """
        if quality_score < 0.7:
            logger.debug(f"Skill not stored: quality {quality_score} < 0.7")
            return

        sig = self._task_signature(task)

        # Skip if already stored with equal or higher quality
        if sig in self._index:
            existing_quality = self._index[sig].get("quality", 0)
            if existing_quality >= quality_score:
                return

        # Evict stale skills if at capacity
        if len(self._index) >= _MAX_SKILLS:
            self._evict_stale()

        # Compress trajectory: keep only tool calls and results
        compressed = self._compress_trajectory(trajectory)

        skill_data = {
            "task": task[:500],
            "label": label or task[:100],
            "trajectory": compressed,
            "quality_score": quality_score,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "use_count": 0,
        }

        # Save skill file
        skill_file = self.storage / f"{sig}.json"
        with self._lock:
            skill_file.write_text(
                json.dumps(skill_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        # Update index
        self._index[sig] = {
            "task": task,
            "label": skill_data["label"],
            "quality": quality_score,
            "created": skill_data["created_at"],
            "last_used": skill_data["last_used"],
            "use_count": 0,
        }
        self._save_index()

        logger.info(
            f"Skill STORED: {sig} ({skill_data['label'][:50]}) "
            f"q={quality_score}"
        )

    def get_context_prompt(self, task: str) -> str:
        """
        Returns a prompt injection snippet if a relevant skill is found.
        
        This snippet guides the agent by showing how a similar task was
        solved previously, encouraging reuse and consistency.
        
        Args:
            task (str): Current task description.
            
        Returns:
            str: Markdown-formatted prompt suffix, or empty string.
        """
        skill = self.find_skill(task)
        if not skill:
            return ""

        steps = skill.get("trajectory", [])
        if not steps:
            return ""

        fuzzy_note = ""
        if skill.get("_fuzzy"):
            fuzzy_note = f" (fuzzy match, similarity={skill.get('_similarity', '?')})"

        lines = [
            f"[SKILL LIBRARY] A similar task was solved before{fuzzy_note}. "
            f"Quality score: {skill.get('quality_score', '?')}/1.0. "
            f"Reference trajectory:"
        ]
        for i, step in enumerate(steps[:10], 1):
            lines.append(
                f"  Step {i}: {step.get('tool','')} "
                f"→ {step.get('result_summary','')[:120]}"
            )
        lines.append(
            "Use this as guidance but adapt to the current task. "
            "Do NOT blindly replay — the context may differ."
        )
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics and high-use metrics for the library."""
        return {
            "total_skills": len(self._index),
            "storage_dir": str(self.storage),
            "top_used": sorted(
                self._index.items(),
                key=lambda x: x[1].get("use_count", 0),
                reverse=True
            )[:5],
        }

    # ── Private helpers ─────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> set:
        """Lowercase, strip punctuation, return set of meaningful words (length > 2)."""
        text = text.lower().translate(
            str.maketrans("", "", string.punctuation)
        )
        return set(w for w in text.split() if len(w) > 2)

    def _load_skill_file(self, sig: str) -> Optional[Dict[str, Any]]:
        """Loads and parses a skill JSON file."""
        skill_file = self.storage / f"{sig}.json"
        if not skill_file.exists():
            return None
        try:
            return json.loads(skill_file.read_text("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to load skill {sig}: {e}")
            return None

    def _record_hit(self, sig: str) -> None:
        """Updates metadata in the index when a skill is successfully retrieved."""
        if sig in self._index:
            self._index[sig]["use_count"] = self._index[sig].get("use_count", 0) + 1
            self._index[sig]["last_used"] = datetime.now().isoformat()
            self._save_index()

    def _evict_stale(self) -> None:
        """Removes skills that haven't been used for 30+ days to free up library space."""
        cutoff = (datetime.now() - timedelta(days=_SKILL_TTL_DAYS)).isoformat()
        stale = [
            sig for sig, meta in self._index.items()
            if meta.get("last_used", meta.get("created", "")) < cutoff
        ]

        # Sort by quality (evict lowest first)
        stale.sort(key=lambda s: self._index[s].get("quality", 0))

        evicted = 0
        for sig in stale:
            skill_file = self.storage / f"{sig}.json"
            if skill_file.exists():
                skill_file.unlink()
            del self._index[sig]
            evicted += 1
            if len(self._index) < _MAX_SKILLS:
                break

        if evicted:
            self._save_index()
            logger.info(f"SkillLibrary evicted {evicted} stale skills")

    @staticmethod
    def _compress_trajectory(
        trajectory: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Minifies a trajectory for storage efficiency.
        
        Args:
            trajectory (List[Dict]): Full execution trace.
            
        Returns:
            List[Dict]: Compressed version containing only critical tool interactions.
        """
        compressed = []
        for step in trajectory:
            if step.get("tool_call") or step.get("type") == "tool":
                tool_call = step.get("tool_call", {})
                compressed.append({
                    "tool": tool_call.get("name", step.get("name", "unknown")),
                    "params_summary": str(
                        tool_call.get("params", step.get("params", {}))
                    )[:250],
                    "result_summary": str(
                        step.get("result", step.get("output", ""))
                    )[:250],
                })
        return compressed

    async def synthesize_skill_from_web(self, task_description: str, model_router: Any, search_context: str = "") -> bool:
        """
        Synthesizes a new skill from web knowledge if it's missing in the local library.
        
        Args:
            task_description: The goal to synthesize a skill for.
            model_router: The LLM model to use for synthesis.
            search_context: Optional pre-fetched documentation or search results.
            
        Returns:
            bool: True if a skill was successfully synthesized and saved, False otherwise.
        """
        sig = self._task_signature(task_description)
        if sig in self._index:
            return True # Already exists
            
        prompt = f"""
You need to synthesize a reusable technical skill (execution trajectory) for the following task:
Task: {task_description}

Context/Docs: {search_context[:4000]}

Generate a simulated, optimal execution trace that an agent should follow to solve this task.
Return it as a JSON array of steps. Each step must have:
- "tool": the tool name (e.g., "run_command", "replace_file_content")
- "params_summary": a brief summary of parameters used
- "result_summary": expected successful result

Ensure the JSON array is the ONLY output.
"""
        try:
            response = await model_router.generate(
                messages=[{"role": "user", "content": prompt}],
                task_hint="think"
            )
            from backend.utils.json_repair import repair_and_parse
            steps, _ = repair_and_parse(response.get("text", "[]"))
            
            if steps and isinstance(steps, list):
                # Fake a score since it's theoretically derived
                quality = 0.85
                self.save_skill(task_description, steps, quality)
                logger.info(f"Synthesized new skill from web for: {task_description[:50]}")
                return True
        except Exception as e:
            logger.warning(f"Failed to synthesize skill from web: {e}")
            
        return False
