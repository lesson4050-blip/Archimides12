"""
Observability utilities for Archimedes.

Provides:
- CorrelatedLogFilter: injects session_id and trace_id into all log records
- JSONFormatter: structured JSON log output for production (ELK/Datadog/CloudWatch)
- configure_global_observability(): root logger setup with correlation
- configure_json_logging(): auto-detect LOG_FORMAT env var for JSON output
"""
import logging
import uuid
import contextvars
from typing import Any, Dict

# Context variables to store session and trace ids per request/task
_session_id = contextvars.ContextVar("session_id", default="-")
_trace_id = contextvars.ContextVar("trace_id", default="-")

def set_observability_context(session_id: str, trace_id: str = None):
    """Set the session and trace ids for the current context."""
    _session_id.set(session_id)
    if not trace_id:
        trace_id = str(uuid.uuid4())
    _trace_id.set(trace_id)
    return trace_id

class CorrelatedLogFilter(logging.Filter):
    """Filter to inject session_id and trace_id into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = _session_id.get()
        record.trace_id = _trace_id.get()
        return True

def setup_correlated_logger(name: str = None) -> logging.Logger:
    """Setup and return a logger configured with correlation IDs."""
    logger = logging.getLogger(name)
    
    # Avoid adding multiple filters if it's already set up
    if not any(isinstance(f, CorrelatedLogFilter) for f in logger.filters):
        logger.addFilter(CorrelatedLogFilter())
        
    # Configure formatter if this is the root logger or we want to override
    # Usually handled globally, but here we can ensure the format is right
    return logger

import json

class JSONFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "session_id": getattr(record, "session_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "logger": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def configure_global_observability(use_json: bool = False):
    """Configure the root logger to use correlated formatter."""
    root_logger = logging.getLogger()
    root_logger.addFilter(CorrelatedLogFilter())
    
    # Update all handlers to show session and trace IDs
    if use_json:
        formatter = JSONFormatter()
    else:
        # Use a custom format that handles missing session_id/trace_id gracefully
        class SafeFormatter(logging.Formatter):
            def format(self, record):
                if not hasattr(record, "session_id"):
                    record.session_id = "-"
                if not hasattr(record, "trace_id"):
                    record.trace_id = "-"
                return super().format(record)
        
        formatter = SafeFormatter(
            '[%(asctime)s] [%(levelname)s] [S:%(session_id)s] [T:%(trace_id)s] %(name)s - %(message)s'
        )
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

def configure_json_logging():
    """Configure JSON logging based on LOG_FORMAT env var."""
    import os
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    if log_format == "json":
        configure_global_observability(use_json=True)
    else:
        configure_global_observability(use_json=False)
