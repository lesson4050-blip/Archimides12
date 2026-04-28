"""
Security middleware for Archimedes API.

Phase 3 hardening:
- Rate limiting per IP
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Session ID validation
- Blocked shell command patterns
"""
import re
import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ─── Rate Limiter ────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter per client IP.
    Default: 60 requests/minute per IP for API endpoints.
    Health checks and static assets are exempt.
    """

    EXEMPT_PATHS = {"/", "/api/health", "/api/v1/health", "/docs", "/openapi.json"}

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._buckets: dict = defaultdict(lambda: {"tokens": requests_per_minute, "last": time.time()})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Exempt health checks and docs
        if path in self.EXEMPT_PATHS or path.startswith("/docs"):
            return await call_next(request)

        # WebSocket connections are not rate-limited
        if "websocket" in request.scope.get("type", ""):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]

        # Refill tokens based on elapsed time
        now = time.time()
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(
            self.rpm,
            bucket["tokens"] + elapsed * (self.rpm / 60)
        )
        bucket["last"] = now

        if bucket["tokens"] < 1:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"}
            )

        bucket["tokens"] -= 1
        return await call_next(request)


# ─── Security Headers ───────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS only if served over HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ─── Input Validation ────────────────────────────────────────────

SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")

def validate_session_id(session_id: str) -> bool:
    """Validate session_id format — alphanumeric, dashes, underscores, max 128 chars."""
    return bool(SESSION_ID_PATTERN.match(session_id))


# ─── Blocked Shell Commands ─────────────────────────────────────

BLOCKED_SHELL_PATTERNS = [
    # Destructive commands
    r"\brm\s+-rf\s+/",              # rm -rf /
    r"\bmkfs\b",                    # format filesystem
    r"\bdd\s+if=",                  # disk destroyer
    r":\(\)\s*\{",                   # fork bomb :(){ :|:& };:
    # Privilege escalation
    r"\bsudo\s+su\b",
    r"\bchmod\s+777\s+/",
    r"\bchown\s+root\b",
    # Network exfiltration
    r"\bcurl\b.*\|\s*bash",         # curl | bash
    r"\bwget\b.*\|\s*sh",          # wget | sh
    r"\bnc\s+-e\b",                 # netcat reverse shell
    r"\b/dev/tcp/",                 # bash reverse shell
    # Container escape
    r"\bnsenter\b",
    r"\bmount\s+-o\s+bind",
    r"\bchroot\b",
    r"\bdocker\s+run\b",
    # Crypto mining
    r"\bxmrig\b",
    r"\bminerd\b",
    r"\bcryptominer\b",
]

BLOCKED_SHELL_RE = re.compile("|".join(BLOCKED_SHELL_PATTERNS), re.IGNORECASE)


def is_command_blocked(command: str) -> bool:
    """Check if a shell command matches any blocked pattern."""
    return bool(BLOCKED_SHELL_RE.search(command))
