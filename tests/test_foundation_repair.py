"""
Archimedes 12 — Foundation Repair Verification Tests.

Tests for all 7 fixes from the hardening protocol:
  FIX-1: is_conversational() no longer catches real questions
  FIX-2: Proactive search helper exists and detects info questions
  FIX-3: Config validation runs and reports status
  FIX-4: Tool initializer has tracking attributes
  FIX-5: Dynamic tool selector filters tools correctly
  FIX-6: bash_security blocks 'cat /etc/passwd'
"""

import os
import sys
import pytest

# Ensure test isolation
os.environ["TESTING"] = "1"
os.environ.setdefault("PYTEST_CURRENT_TEST", "yes")


# ── FIX-1: is_conversational tests ──────────────────────────────

class TestIsConversational:
    """Verify is_conversational() only matches greetings, not questions."""
    
    @pytest.fixture(autouse=True)
    def import_func(self):
        from backend.agent.orchestration.orchestrator import is_conversational
        self.is_conversational = is_conversational
    
    # Should return True (greetings/farewells)
    @pytest.mark.parametrize("text", [
        "привет",
        "привет!",
        "Здравствуй",
        "hello",
        "hi!",
        "Hey",
        "добрый день",
        "спасибо",
        "пока",
        "bye",
        "thanks!",
    ])
    def test_greetings_match(self, text):
        assert self.is_conversational(text) is True, f"Expected True for greeting: {text!r}"
    
    # Should return False (real questions — THIS WAS THE BUG)
    @pytest.mark.parametrize("text", [
        "What is Python?",
        "who created Linux",
        "how to install npm",
        "explain REST API",
        "найди новости о Python",
        "что такое машинное обучение",
        "как установить Docker",
        "где находится файл config",
        "расскажи про React",
        "сколько стоит GPT-4",
        "tell me about FastAPI",
        "search for latest AI news",
        "latest news today",
    ])
    def test_questions_do_not_match(self, text):
        assert self.is_conversational(text) is False, f"Expected False for question: {text!r}"
    
    # Meta-questions about the agent should still match
    @pytest.mark.parametrize("text", [
        "что ты умеешь",
        "кто ты",
    ])
    def test_meta_questions_match(self, text):
        assert self.is_conversational(text) is True, f"Expected True for meta-question: {text!r}"

    # Short non-greeting text should NOT match (was broken before FIX-1)
    @pytest.mark.parametrize("text", [
        "fix the bug",
        "run tests",
        "ls -la",
        "deploy now",
    ])
    def test_short_commands_do_not_match(self, text):
        assert self.is_conversational(text) is False, f"Expected False for command: {text!r}"


# ── ДИАГНОЗ-1 FIX: classify_task() short-task routing ──────────

class TestClassifyTaskRouting:
    """Verify classify_task() does NOT silently route short real tasks to 'direct'.
    
    The original defect: `if len(text) < 15: return "simple", "direct"`
    sent ALL short inputs to conversational mode without tools.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("text,forbidden_strategy", [
        ("fix the bug", "direct"),
        ("run tests", "direct"),
        ("debug this", "direct"),
        ("deploy now", "direct"),  # no routing rule, but should NOT be "direct" blindly
        ("create API", "direct"),
        ("find errors", "direct"),
        ("исправь баг", "direct"),
        ("напиши код", "direct"),
    ])
    async def test_short_real_tasks_not_direct(self, text, forbidden_strategy):
        from backend.agent.orchestration.orchestrator import classify_task
        complexity, strategy = await classify_task(text, router=None)
        assert strategy != forbidden_strategy, (
            f"Short task {text!r} was routed to '{strategy}' "
            f"(complexity={complexity}). Expected NOT 'direct'."
        )
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("text", [
        "ok",
        "yes",
        "hmm",
        "no",
    ])
    async def test_genuinely_trivial_inputs_fallback(self, text):
        """Genuinely trivial short inputs should fall through to some fallback,
        but NOT crash."""
        from backend.agent.orchestration.orchestrator import classify_task
        complexity, strategy = await classify_task(text, router=None)
        # Just verify it returns something valid without crashing
        assert isinstance(complexity, str)
        assert isinstance(strategy, str)


# ── FIX-3: Config validation tests ─────────────────────────────

class TestConfigValidation:
    """Verify config validation runs without crashing."""
    
    def test_validate_config_returns_dict(self):
        from backend.config import validate_config
        result = validate_config()
        assert isinstance(result, dict)
        assert "ok" in result
        assert "warnings" in result
        assert "errors" in result
    
    def test_validate_config_lists_are_lists(self):
        from backend.config import validate_config
        result = validate_config()
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)


# ── FIX-5: Tool selector tests ──────────────────────────────────

class TestToolSelector:
    """Verify dynamic tool selection filters correctly."""
    
    @pytest.fixture
    def mock_tools(self):
        """Create mock tool definitions."""
        tool_names = [
            "search", "shell", "file", "message",
            "python_repl", "browser", "canvas", "video",
            "audio", "deploy", "monitor", "infra",
            "image_gen", "git", "grep", "glob",
            "web_read", "parallel_search", "vector_search",
            "code_edit", "fast_linter", "notebook",
        ]
        return [
            {"function": {"name": name, "description": f"mock {name}"}}
            for name in tool_names
        ]
    
    def test_essential_tools_always_included(self, mock_tools):
        from backend.agent.tool_selector import select_tools, ESSENTIAL_TOOLS
        result = select_tools("hello world", mock_tools)
        result_names = {t["function"]["name"] for t in result}
        for essential in ESSENTIAL_TOOLS:
            if essential in {t["function"]["name"] for t in mock_tools}:
                assert essential in result_names, f"Essential tool {essential} missing"
    
    def test_max_tools_limit(self, mock_tools):
        from backend.agent.tool_selector import select_tools, MAX_TOOLS
        result = select_tools("search and analyze and write code and deploy and browse website", mock_tools)
        assert len(result) <= MAX_TOOLS, f"Got {len(result)} tools, max is {MAX_TOOLS}"
    
    def test_coding_profile_includes_repl(self, mock_tools):
        from backend.agent.tool_selector import select_tools
        result = select_tools("write a Python function", mock_tools)
        result_names = {t["function"]["name"] for t in result}
        assert "python_repl" in result_names
    
    def test_excluded_tools_filtered(self, mock_tools):
        from backend.agent.tool_selector import select_tools
        result = select_tools("write code", mock_tools, excluded_tools=["shell"])
        result_names = {t["function"]["name"] for t in result}
        assert "shell" not in result_names
    
    def test_research_profile(self, mock_tools):
        from backend.agent.tool_selector import select_tools
        result = select_tools("найди последние новости", mock_tools)
        result_names = {t["function"]["name"] for t in result}
        assert "web_read" in result_names or "parallel_search" in result_names


# ── FIX-6: Bash security tests ──────────────────────────────────

class TestBashSecurity:
    """Verify bash_security blocks sensitive file reads."""
    
    @pytest.fixture(autouse=True)
    def import_func(self):
        from backend.tools.bash_security import validate_command
        self.validate = validate_command
    
    @pytest.mark.parametrize("cmd", [
        "cat /etc/passwd",
        "cat /etc/shadow",
        "head /etc/sudoers",
        "tail /etc/shadow",
        "less /etc/passwd",
        "strings /etc/shadow",
    ])
    def test_sensitive_file_reads_blocked(self, cmd):
        result = self.validate(cmd)
        assert not result.allowed, f"Expected BLOCKED for: {cmd!r}, got: {result.message}"
    
    @pytest.mark.parametrize("cmd", [
        "ls -la",
        "cat README.md",
        "echo hello",
        "python --version",
        "cat /var/log/app.log",
        "head -n 10 output.txt",
    ])
    def test_safe_commands_allowed(self, cmd):
        result = self.validate(cmd)
        assert result.allowed, f"Expected ALLOWED for: {cmd!r}, got: {result.message}"
    
    def test_fork_bomb_blocked(self):
        result = self.validate(":(){ :|:& };:")
        assert not result.allowed
    
    def test_rm_rf_root_blocked(self):
        result = self.validate("rm -rf /")
        assert not result.allowed


# ── FIX-4: Tool initializer tracking ────────────────────────────

class TestToolInitializerTracking:
    """Verify tool initializer has tracking attributes."""
    
    def test_has_tracking_attributes(self):
        from backend.agent.tool_initializer import ToolInitializer
        
        # Create with mock objects
        class MockRegistry:
            tools = {}
            def register(self, *a): pass
        class MockAgent:
            pass
        
        init = ToolInitializer(MockRegistry(), "test", MockAgent())
        assert hasattr(init, "_registered")
        assert hasattr(init, "_failed")
        assert hasattr(init, "_critical_tools")
        assert isinstance(init._registered, list)
        assert isinstance(init._failed, list)
        assert "search" in init._critical_tools
        assert "file" in init._critical_tools
