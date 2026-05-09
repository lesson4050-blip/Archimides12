from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:14b"
    
    TAVILY_API_KEY: str = ""
    EXA_API_KEY: str = ""
    BRAVE_API_KEY: str = ""
    
    # Image Generation
    IMAGE_CRITIQUE_MODEL: str = "gemini-3.1-flash"
    
    # Sandbox
    SANDBOX_IMAGE: str = "archimedes-sandbox:latest"
    SANDBOX_MAX_CONTAINERS: int = 3
    SANDBOX_INACTIVITY_TIMEOUT: int = 3600  # 1 hour
    SANDBOX_SHELL_TIMEOUT: int = 60
    SANDBOX_SHELL_MAX_TIMEOUT: int = 300
    
    # Agent
    AGENT_MAX_ITERATIONS: int = 20
    AGENT_MAX_CONTEXT_TOKENS: int = 128000
    CONTEXT_SUMMARIZATION_THRESHOLD: int = 120000
    CONTEXT_PRESERVE_RECENT: int = 3
    USE_MULTI_AGENT: bool = True  # Feature flag for Phase 4
    
    # Database — PostgreSQL (production) or SQLite (dev fallback)
    DATABASE_URL: str = "postgresql+asyncpg://archimedes:archimedes@localhost:5432/archimedes"
    DATABASE_URL_SQLITE: str = "sqlite+aiosqlite:///./archemidas.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = ""
    
    # Vector DB
    CHROMA_DB_PATH: str = "./data/chroma_db"  # Default; override in .env for Docker (/app/data/chroma_db)
    CHROMA_MAX_DOCS_PER_USER: int = 10000
    CHROMA_TTL_DAYS: int = 90
    
    # Auth / JWT — IMPORTANT: override JWT_SECRET_KEY in .env for production!
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    AUTH_ENABLED: bool = True
    
    # MCP
    MCP_SERVER_PORT: int = 8002
    MCP_EXTERNAL_SERVERS: Dict[str, Any] = {
        "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]}
    }
    
    # Nango
    NANGO_PUBLIC_KEY: str = ""
    NANGO_SECRET_KEY: str = ""
    NANGO_BASE_URL: str = "http://localhost:3003"
    
    # Frontend/WebSocket
    NEXT_PUBLIC_WS_URL: str = "ws://localhost:8000/ws"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=str(_env_path), env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_and_isolate(self) -> "Settings":
        import os
        is_testing = "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or os.environ.get("TESTING") == "1"
        if is_testing:
            # Force SQLite and disable Redis during tests
            self.DATABASE_URL = self.DATABASE_URL_SQLITE
            self.REDIS_URL = ""
            
        if self.AUTH_ENABLED:
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                # During tests, we might want to allow short keys if not specifically testing security
                if not is_testing:
                    raise ValueError(
                        "SECURITY: JWT_SECRET_KEY must be at least 32 chars when "
                        "AUTH_ENABLED=True."
                    )
        return self

settings = Settings()


# ── FIX-3: Startup Configuration Validation ──

import logging as _logging

_config_logger = _logging.getLogger("backend.config")


def validate_config() -> dict:
    """Validate configuration and log clear warnings for missing/weak settings.
    
    Returns a dict with validation results:
        {"ok": bool, "warnings": list[str], "errors": list[str]}
    
    Called at import time — does NOT crash the server, only logs.
    """
    warnings = []
    errors = []
    
    # Check LLM keys — at least ONE must be set
    llm_keys = {
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GOOGLE_API_KEY": settings.GOOGLE_API_KEY,
    }
    active_llm = {k: v for k, v in llm_keys.items() if v}
    if not active_llm:
        errors.append(
            "NO LLM API KEY SET: Set at least one of GROQ_API_KEY or "
            "GOOGLE_API_KEY in .env. Agent will fail on all requests."
        )
    else:
        _config_logger.info(f"LLM keys active: {', '.join(active_llm.keys())}")
    
    # Check search keys
    search_keys = {
        "TAVILY_API_KEY": settings.TAVILY_API_KEY,
        "BRAVE_API_KEY": settings.BRAVE_API_KEY,
    }
    active_search = {k for k, v in search_keys.items() if v}
    if not active_search:
        warnings.append(
            "No search API key set (TAVILY_API_KEY or BRAVE_API_KEY). "
            "Search will fall back to DuckDuckGo (lower quality)."
        )
    else:
        _config_logger.info(f"Search keys active: {', '.join(active_search)}")
    
    # Check JWT in production
    if settings.AUTH_ENABLED and settings.JWT_SECRET_KEY:
        if settings.JWT_SECRET_KEY == "change-me-in-production":
            errors.append(
                "JWT_SECRET_KEY is set to the default placeholder. "
                "Generate a real key: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
    
    # Log results
    for w in warnings:
        _config_logger.warning(f"CONFIG WARNING: {w}")
    for e in errors:
        _config_logger.error(f"CONFIG ERROR: {e}")
    
    if not warnings and not errors:
        _config_logger.info("CONFIG OK: All critical settings validated")
    
    return {"ok": len(errors) == 0, "warnings": warnings, "errors": errors}


# Run validation at import time
_config_validation = validate_config()

