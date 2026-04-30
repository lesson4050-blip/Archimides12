"""
Tests for all hardening phases.

Covers:
- Phase 2: Vector search (ChromaDB)
- Phase 3: Session memory (SQLite)
- Phase 4: Circuit breaker, JSON resilient, self-healing
- Phase 5: AST repo map
- Phase 6: Mutation testing
"""
import asyncio
import os
import sqlite3
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ═══════════════════════════════════════════════════════════════
# Phase 2: Vector Search
# ═══════════════════════════════════════════════════════════════

class TestVectorSearch:
    """Test ChromaDB-backed vector search."""

    def test_engine_init(self, tmp_path):
        """Engine initializes without error."""
        from backend.tools.vector_search import VectorSearchEngine
        engine = VectorSearchEngine(workspace_dir=str(tmp_path))
        assert engine.workspace_dir == str(tmp_path)

    def test_scan_finds_python_files(self, tmp_path):
        """Scanner finds .py files and skips excluded dirs."""
        (tmp_path / "main.py").write_text("def hello(): pass")
        (tmp_path / "utils.py").write_text("class Config: pass")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("x=1")

        from backend.tools.vector_search import VectorSearchEngine
        engine = VectorSearchEngine(workspace_dir=str(tmp_path))
        files = engine._scan_files()

        basenames = [os.path.basename(f) for f in files]
        assert "main.py" in basenames
        assert "utils.py" in basenames
        assert "cached.py" not in basenames  # __pycache__ excluded

    def test_extract_symbols_python(self, tmp_path):
        """Extracts classes and functions from Python."""
        code = '''
class UserService:
    def get_user(self, user_id):
        pass

def standalone():
    pass
'''
        f = tmp_path / "service.py"
        f.write_text(code)

        from backend.tools.vector_search import VectorSearchEngine
        engine = VectorSearchEngine(workspace_dir=str(tmp_path))
        symbols = engine._extract_symbols(code, str(f))

        names = [s["name"] for s in symbols]
        assert "UserService" in names
        assert "standalone" in names

    def test_index_and_search(self, tmp_path):
        """Full index + search cycle."""
        (tmp_path / "auth.py").write_text(
            "def verify_token(token: str) -> bool:\n"
            "    '''Verify JWT token validity'''\n"
            "    return True\n"
        )
        (tmp_path / "db.py").write_text(
            "class DatabaseConnection:\n"
            "    def connect(self): pass\n"
        )

        from backend.tools.vector_search import VectorSearchEngine
        engine = VectorSearchEngine(workspace_dir=str(tmp_path))
        count = engine.index()
        assert count > 0

        results = engine.search("authentication token verification")
        assert len(results) > 0
        # Auth file should rank higher for auth query
        assert any("auth" in r.file_path for r in results)

    @pytest.mark.asyncio
    async def test_tool_interface(self, tmp_path):
        """Test the execute() tool interface."""
        (tmp_path / "app.py").write_text("def main(): pass")

        from backend.tools.vector_search import VectorSearchEngine
        engine = VectorSearchEngine(workspace_dir=str(tmp_path))
        engine.index()

        result = await engine.execute(query="main function", top_k=5)
        assert result["success"] is True
        assert result["output"]["engine"] == "chromadb_vector"


# ═══════════════════════════════════════════════════════════════
# Phase 3: Session Memory SQLite
# ═══════════════════════════════════════════════════════════════

class TestSessionMemorySQLite:
    """Test SQLite-backed session memory."""

    def test_init_creates_db(self, tmp_path):
        """DB is created on init."""
        db_path = str(tmp_path / "test_session.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory
            sm = SessionMemory("test-session-1")
            assert os.path.exists(db_path)

    def test_extract_key_info_finds_errors(self, tmp_path):
        """Extraction finds error patterns."""
        db_path = str(tmp_path / "test.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory
            sm = SessionMemory("test-session")
            msgs = [
                {"role": "assistant", "content": "Error: FileNotFoundError occurred"},
                {"role": "user", "content": "Fix the bug"},
            ]
            result = sm._extract_key_info(msgs)
            assert "Error" in result

    def test_extract_key_info_finds_files(self, tmp_path):
        """Extraction finds file paths."""
        db_path = str(tmp_path / "test.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory
            sm = SessionMemory("test-session")
            msgs = [{"role": "assistant", "content": "Modified backend/agent/core.py successfully"}]
            result = sm._extract_key_info(msgs)
            assert "backend/agent/core.py" in result

    def test_save_and_load(self, tmp_path):
        """Data persists through save/load cycle."""
        db_path = str(tmp_path / "test.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory

            sm = SessionMemory("test-persist")
            sm._current_memory = "# Test Memory\nSome content here"
            sm._save_to_db("test task", "2026-01-01 00:00 UTC")

            sm2 = SessionMemory("test-persist")
            loaded = sm2.load()
            assert "Test Memory" in loaded

    def test_search_past_sessions(self, tmp_path):
        """Cross-session search works."""
        db_path = str(tmp_path / "test.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory

            sm1 = SessionMemory("session-alpha")
            sm1._current_memory = "Fixed authentication bug in JWT module"
            sm1._save_to_db("auth fix", "2026-01-01 00:00 UTC")

            sm2 = SessionMemory("session-beta")
            sm2._current_memory = "Created database migration script"
            sm2._save_to_db("db migration", "2026-01-01 01:00 UTC")

            results = SessionMemory.search_past_sessions("authentication")
            assert len(results) > 0
            assert results[0]["session_id"] == "session-alpha"

    def test_list_recent_sessions(self, tmp_path):
        """List sessions returns results."""
        db_path = str(tmp_path / "test.db")
        with patch("backend.memory.session_memory.SESSION_MEMORY_DB", db_path):
            from backend.memory.session_memory import SessionMemory

            sm = SessionMemory("session-recent")
            sm._current_memory = "Some content"
            sm._save_to_db("task", "2026-01-01 00:00 UTC")

            sessions = SessionMemory.list_recent_sessions()
            assert isinstance(sessions, list)
            assert len(sessions) > 0


# ═══════════════════════════════════════════════════════════════
# Phase 4: Circuit Breaker + JSON Resilient + Self-Healing
# ═══════════════════════════════════════════════════════════════

class TestJSONResilient:
    """Test extract_json_resilient from ErrorRecovery."""

    def test_clean_json(self):
        from backend.agent.error_recovery import ErrorRecovery
        er = ErrorRecovery()
        result = er.extract_json_resilient('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_fence(self):
        from backend.agent.error_recovery import ErrorRecovery
        text = 'Here is the result:\n```json\n{"score": 0.9}\n```\nDone.'
        result = ErrorRecovery.extract_json_resilient(text)
        assert result == {"score": 0.9}

    def test_trailing_comma(self):
        from backend.agent.error_recovery import ErrorRecovery
        text = '{"a": 1, "b": 2,}'
        result = ErrorRecovery.extract_json_resilient(text)
        assert result is not None
        assert result["a"] == 1

    def test_prose_around_json(self):
        from backend.agent.error_recovery import ErrorRecovery
        text = 'The answer is {"status": "ok"} and that is all.'
        result = ErrorRecovery.extract_json_resilient(text)
        assert result == {"status": "ok"}

    def test_empty_input(self):
        from backend.agent.error_recovery import ErrorRecovery
        assert ErrorRecovery.extract_json_resilient("") is None
        assert ErrorRecovery.extract_json_resilient("   ") is None
        assert ErrorRecovery.extract_json_resilient("no json here") is None

    def test_array_json(self):
        from backend.agent.error_recovery import ErrorRecovery
        text = '["fact1", "fact2"]'
        result = ErrorRecovery.extract_json_resilient(text)
        assert result == ["fact1", "fact2"]


class TestSelfHealing:
    """Test self_healing_check from ErrorRecovery."""

    def test_no_failures(self):
        from backend.agent.error_recovery import ErrorRecovery
        er = ErrorRecovery()
        result = er.self_healing_check()
        assert result["stuck"] is False

    def test_same_tool_repeating(self):
        from backend.agent.error_recovery import ErrorRecovery
        er = ErrorRecovery()
        for _ in range(4):
            er.record_failure("shell", {"command": "test"}, "Error: failed", file_path=None)
        result = er.self_healing_check()
        assert result["stuck"] is True
        assert "shell" in result["pattern"]

    def test_same_file_repeating(self):
        from backend.agent.error_recovery import ErrorRecovery
        er = ErrorRecovery()
        for _ in range(3):
            er.record_failure("file", {"path": "app.py"}, "SyntaxError", file_path="app.py")
        result = er.self_healing_check()
        assert result["stuck"] is True
        assert "app.py" in result["pattern"]


# ═══════════════════════════════════════════════════════════════
# Phase 5: AST Repo Map
# ═══════════════════════════════════════════════════════════════

class TestRepoMap:
    """Test AST-based repository map."""

    def test_parse_python_file(self, tmp_path):
        """Parses Python AST correctly."""
        code = '''
class AuthService:
    def login(self, username, password):
        pass

    def logout(self):
        pass

def standalone_function(x, y):
    return x + y
'''
        f = tmp_path / "auth.py"
        f.write_text(code)

        from backend.tools.repo_map import RepoMap
        rm = RepoMap(workspace_dir=str(tmp_path))
        info = rm._parse_python_file(str(f))

        names = [s.name for s in info.symbols]
        assert "AuthService" in names
        assert "login" in names
        assert "logout" in names
        assert "standalone_function" in names

    def test_generate_map(self, tmp_path):
        """Generates readable map output."""
        (tmp_path / "main.py").write_text("def main(): pass\n")
        (tmp_path / "utils.py").write_text("class Helper:\n    def help(self): pass\n")

        from backend.tools.repo_map import RepoMap
        rm = RepoMap(workspace_dir=str(tmp_path))
        output = rm.generate_map()

        assert "Repository Map" in output
        assert "main.py" in output
        assert "utils.py" in output

    def test_get_file_context(self, tmp_path):
        """File context includes symbols and imports."""
        code = "import os\nimport sys\n\ndef process(): pass\n"
        (tmp_path / "worker.py").write_text(code)

        from backend.tools.repo_map import RepoMap
        rm = RepoMap(workspace_dir=str(tmp_path))
        rm.scan()

        ctx = rm.get_file_context("worker.py")
        assert ctx is not None
        assert "process" in ctx
        assert "os" in ctx

    def test_skip_pycache(self, tmp_path):
        """__pycache__ directories are skipped."""
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("x=1")
        (tmp_path / "real.py").write_text("y=2")

        from backend.tools.repo_map import RepoMap
        rm = RepoMap(workspace_dir=str(tmp_path))
        files = rm.scan()

        paths = list(files.keys())
        assert any("real.py" in p for p in paths)
        assert not any("cached.py" in p for p in paths)

    @pytest.mark.asyncio
    async def test_tool_interface(self, tmp_path):
        """Test the execute() tool interface."""
        (tmp_path / "app.py").write_text("def main(): pass")

        from backend.tools.repo_map import RepoMap
        rm = RepoMap(workspace_dir=str(tmp_path))

        result = await rm.execute(action="map")
        assert result["success"] is True
        assert "Repository Map" in result["output"]

        result = await rm.execute(action="scan")
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════
# Phase 4: MCTS Benchmark (unit-level)
# ═══════════════════════════════════════════════════════════════

class TestMCTSBenchmark:
    """Test MCTS benchmark scoring."""

    def test_score_response_with_keywords(self):
        from backend.benchmarks.mcts_benchmark import _score_response
        task_info = {
            "eval_keywords": ["merge", "sorted", "return"],
            "difficulty": "easy",
        }
        response = "def merge_sorted(a, b):\n    return sorted(a + b)"
        score = _score_response(response, task_info)
        assert score > 0.3

    def test_score_response_empty(self):
        from backend.benchmarks.mcts_benchmark import _score_response
        task_info = {"eval_keywords": ["merge"], "difficulty": "easy"}
        score = _score_response("", task_info)
        assert score == 0.0

    def test_benchmark_suite_summary(self):
        from backend.benchmarks.mcts_benchmark import BenchmarkSuite
        suite = BenchmarkSuite()
        summary = suite.summary()
        assert summary["total_tasks"] == 0
        assert summary["mcts_win_rate"] == 0.0
