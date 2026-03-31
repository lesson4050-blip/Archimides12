from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "hf.co/bartowski/Qwen2.5-32B-Instruct-GGUF:Q4_K_M"
    
    TAVILY_API_KEY: str = ""
    
    # Sandbox
    SANDBOX_IMAGE: str = "archemidas-sandbox:latest"
    SANDBOX_MAX_CONTAINERS: int = 3
    SANDBOX_INACTIVITY_TIMEOUT: int = 1800  # 30 minutes
    SANDBOX_SHELL_TIMEOUT: int = 60
    SANDBOX_SHELL_MAX_TIMEOUT: int = 300
    
    # Agent
    AGENT_MAX_ITERATIONS: int = 20
    AGENT_MAX_CONTEXT_TOKENS: int = 8192
    
    # DB
    DATABASE_URL: str = "sqlite+aiosqlite:///./archemidas.db"
    
    # Frontend/WebSocket
    NEXT_PUBLIC_WS_URL: str = "ws://localhost:8000/ws"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
