"""
ThreatPath Application Configuration
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    
    # FalkorDB settings
    FALKORDB_HOST: str = "127.0.0.1"
    FALKORDB_PORT: int = 6379
    FALKORDB_PASSWORD: Optional[str] = None
    FALKORDB_GRAPH: str = "threatpath_dev"
    
    # LLM Settings (supports mock fallback)
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = ""
    LLM_API_KEY: Optional[str] = None
    
    # Agent behavior
    AGENT_MAX_TOOL_ROUNDS: int = 6
    AGENT_TOOL_TIMEOUT_SECONDS: int = 10
    ENABLE_SIMULATED_RESPONSES: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
