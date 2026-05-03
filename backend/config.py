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
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:26b"
    
    TAVILY_API_KEY: str = ""
    EXA_API_KEY: str = ""
    
    # Image Generation
    IMAGE_CRITIQUE_MODEL: str = "gemini-2.5-flash"
    
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
    AUTH_ENABLED: bool = True  # Production default; set False in .env for dev
    
    # MCP
    MCP_SERVER_PORT: int = 8002
    MCP_EXTERNAL_SERVERS: Dict[str, Any] = {
        "google-search": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-google-search"]},
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
