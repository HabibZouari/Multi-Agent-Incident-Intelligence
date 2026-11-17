"""Central application settings, loaded from environment variables / `.env`."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ResolveAI"
    app_env: str = "development"
    log_level: str = "INFO"

    # Database. Defaults to a local SQLite file so no credentials live in code; set DATABASE_URL
    # (e.g. in .env) to use PostgreSQL + pgvector.
    database_url: str = "sqlite:///./resolveai_local.db"

    # LLM provider (Anthropic API or any Anthropic-compatible proxy)
    anthropic_api_key: str = ""
    anthropic_base_url: str | None = None
    default_model: str = "claude-sonnet-5-5"

    # Retrieval
    embedding_dim: int = Field(default=512, ge=64, le=4096)

    # MCP server
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8001
    mcp_transport: str = "stdio"  # stdio | streamable-http | sse

    # API. When API_KEY is set, every /api/* request must send it in the X-API-Key header.
    api_key: str = ""
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_auth_enabled(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
