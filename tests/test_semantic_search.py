"""Tests for semantic codebase search."""
import os
import tempfile
from backend.tools.semantic_search import SemanticSearchEngine


class TestSemanticSearch:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, "auth.py"), "w") as f:
            f.write('def authenticate_user(username, password):\n    """Verify user credentials."""\n    return True\n')
        with open(os.path.join(self.tmpdir, "math_utils.py"), "w") as f:
            f.write('def calculate_fibonacci(n):\n    """Calculate nth Fibonacci number."""\n    if n <= 1: return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)\n')

    def test_index_finds_symbols(self):
        engine = SemanticSearchEngine(self.tmpdir)
        count = engine.index()
        assert count >= 2

    def test_search_by_meaning(self):
        engine = SemanticSearchEngine(self.tmpdir)
        engine.index()
        results = engine.search("authenticate verify")
        assert len(results) > 0
        assert "authenticate" in results[0].symbol_name.lower()

    def test_search_fibonacci(self):
        engine = SemanticSearchEngine(self.tmpdir)
        engine.index()
        results = engine.search("calculate fibonacci")
        assert len(results) > 0
        assert "fibonacci" in results[0].symbol_name.lower()

    def test_empty_query_returns_empty(self):
        engine = SemanticSearchEngine(self.tmpdir)
        engine.index()
        results = engine.search("")
        assert len(results) == 0
