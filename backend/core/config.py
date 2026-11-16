import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "ResolveAI"
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:CHANGE_ME@localhost:5432/resolveai")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_base_url: Optional[str] = os.getenv("ANTHROPIC_BASE_URL", None)
    default_model: str = os.getenv("DEFAULT_MODEL", "auto/best-coding")
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "8001"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
