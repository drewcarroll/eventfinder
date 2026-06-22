"""Application settings.

Environment configuration lives in the infrastructure layer only. Domain
and application layers never read environment variables directly.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed environment configuration."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "Event Swiper API"
    environment: str = "development"
    debug: bool = True

    # PostgreSQL
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/event_swiper"
    )

    # Anthropic Claude
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Tavily
    tavily_api_key: str = ""

    # Firebase
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""

    # CORS
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
