"""Tests for observability module (test 1.11)."""
import logging
import pytest
from backend.utils.observability import (
    set_observability_context,
    CorrelatedLogFilter,
    setup_correlated_logger,
    configure_global_observability,
    _session_id,
    _trace_id,
)


@pytest.fixture(autouse=True)
def _cleanup_root_logger():
    """Remove any CorrelatedLogFilter from the root logger after each test to avoid test pollution."""
    yield
    root = logging.getLogger()
    root.filters = [f for f in root.filters if not isinstance(f, CorrelatedLogFilter)]
    # Also clean up any handlers with the format containing session_id
    for handler in root.handlers:
        if hasattr(handler, 'formatter') and handler.formatter:
            fmt = handler.formatter._fmt if hasattr(handler.formatter, '_fmt') else ''
            if 'session_id' in fmt:
                handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))


def test_set_observability_context_with_trace():
    """Setting context with explicit trace_id should store both."""
    result = set_observability_context("sess-1", "trace-abc")
    assert result == "trace-abc"
    assert _session_id.get() == "sess-1"
    assert _trace_id.get() == "trace-abc"


def test_set_observability_context_auto_trace():
    """Setting context without trace_id should auto-generate UUID."""
    result = set_observability_context("sess-2")
    assert len(result) > 0
    assert "-" in result  # UUID format


def test_correlated_log_filter():
    """Filter should inject session_id and trace_id into log records."""
    set_observability_context("test-session", "test-trace")
    f = CorrelatedLogFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=None, exc_info=None
    )
    assert f.filter(record) is True
    assert record.session_id == "test-session"
    assert record.trace_id == "test-trace"


def test_setup_correlated_logger():
    """Should return a logger with CorrelatedLogFilter attached."""
    logger = setup_correlated_logger("test.obs")
    assert any(isinstance(f, CorrelatedLogFilter) for f in logger.filters)
    # Second call should NOT add duplicate filter
    setup_correlated_logger("test.obs")
    filter_count = sum(1 for f in logger.filters if isinstance(f, CorrelatedLogFilter))
    assert filter_count == 1
    # Cleanup: remove filter from this specific logger too
    logger.filters = [f for f in logger.filters if not isinstance(f, CorrelatedLogFilter)]


def test_configure_global_observability():
    """Global configuration should add filter to root logger."""
    configure_global_observability()
    root = logging.getLogger()
    assert any(isinstance(f, CorrelatedLogFilter) for f in root.filters)
    # Cleanup is handled by autouse fixture
