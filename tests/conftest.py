"""
Shared test fixtures for Archimedes test suite.
"""

import pytest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test_archimedes.db")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")


@pytest.fixture
def sample_messages():
    """Sample conversation history for context manager tests."""
    return [
        {"role": "system", "content": "You are Archimedes, an AI agent."},
        {"role": "user", "content": "Hello, create a file called test.py"},
        {"role": "assistant", "content": "I'll create that file for you."},
        {"role": "tool", "content": "File created successfully", "tool_call_id": "call_1"},
        {"role": "assistant", "content": "Done! The file test.py has been created."},
    ]
