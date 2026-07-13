from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Neo4j ──────────────────────────────────────────────────────────────
    # We use these credentials to establish a connection to our graph database.
    # Without these, the entire backend will start but fail to process any scheme logic,
    # as the graph traversal depends entirely on a live Neo4j instance.
    NEO4J_URI: str = "neo4j+s://your-instance.databases.neo4j.io"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str  # required – no default

    # ── Groq (Primary AI) ──────────────────────────────────────────────────
    # Groq provides fast inference with high rate limits on the free tier.
    # Set this to use Groq as the primary AI provider.
    GROQ_API_KEY: str = ""  # optional – set to enable Groq

    # ── Google Gemini (Fallback AI) ────────────────────────────────────────
    # Used as fallback when Groq is unavailable, and for web enrichment.
    GEMINI_API_KEY: str = ""  # optional – set to enable Gemini fallback

    # ── Validators ──────────────────────────────────────────────────────────
    @field_validator("NEO4J_PASSWORD", mode="before")
    @classmethod
    def must_not_be_empty(cls, v: Optional[str], info) -> str:  # noqa: ANN001
        if not v or not v.strip():
            raise ValueError(
                f"Environment variable '{info.field_name}' is required and must not be empty. "
                f"Copy .env.example to .env and fill in the values."
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of Settings.

    Raises:
        pydantic_settings.ValidationError: if any required env var is missing.
    """
    return Settings()
