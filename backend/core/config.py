"""Central application settings, loaded from environment variables / `.env`."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ResolveAI"
    app_env: str = "development"
    log_level: str = "INFO"

    # Database (PostgreSQL + pgvector in production, SQLite fallback for local dev)
    database_url: str = "postgresql://postgres:CHANGE_ME@localhost:5432/resolveai"

    # LLM provider (Anthropic API or any Anthropic-compatible proxy)
    anthropic_api_key: str = ""
    anthropic_base_url: str | None = None
    default_model: str = "claude-sonnet-5-5"

    # Retrieval
    embedding_dim: int = Field(default=512, ge=64, le=4096)

    # MCP server
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8001

    # API
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
