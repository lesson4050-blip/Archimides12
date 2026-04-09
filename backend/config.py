from pydantic_settings import BaseSettings, SettingsConfigDict
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
    
    # Image Generation
    IMAGE_CRITIQUE_MODEL: str = "gemini-2.5-flash"
    
    # Sandbox
    SANDBOX_IMAGE: str = "cosmo-sandbox:latest"
    SANDBOX_MAX_CONTAINERS: int = 3
    SANDBOX_INACTIVITY_TIMEOUT: int = 1800  # 30 minutes
    SANDBOX_SHELL_TIMEOUT: int = 60
    SANDBOX_SHELL_MAX_TIMEOUT: int = 300
    
    # Agent
    AGENT_MAX_ITERATIONS: int = 20
    AGENT_MAX_CONTEXT_TOKENS: int = 16384
    
    # DB
    DATABASE_URL: str = "sqlite+aiosqlite:///./archemidas.db"
    
    # Frontend/WebSocket
    NEXT_PUBLIC_WS_URL: str = "ws://localhost:8000/ws"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=str(_env_path), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
