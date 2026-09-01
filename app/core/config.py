from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BrandPulse API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    database_url: str = "postgresql+asyncpg://brandpulse:brandpulse_dev@localhost:5432/brandpulse"
    test_database_url: str = (
        "postgresql+asyncpg://brandpulse:brandpulse_dev@localhost:5432/brandpulse_test"
    )
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    llm_max_retries: int = Field(default=1, ge=0, le=5)
    ragflow_base_url: str = ""
    ragflow_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
