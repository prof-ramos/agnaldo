"""Centralized configuration using Pydantic Settings."""

from enum import Enum
from threading import Lock

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment options."""

    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Core secrets
    DISCORD_BOT_TOKEN: str
    SUPABASE_URL: str
    SUPABASE_DB_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    OPENAI_API_KEY: str

    # Environment
    ENVIRONMENT: Environment = Environment.DEV
    LOG_LEVEL: str = "INFO"

    # Discord configuration
    DISCORD_INTENTS: list[str] = Field(default=["message_content", "guild_messages", "dm_messages"])

    # OpenAI configuration
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # SentenceTransformer configuration
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"

    # Cache configuration
    CACHE_MAX_SIZE: int = 1000
    CACHE_TTL: int = 300

    # Rate limiting
    RATE_LIMIT_GLOBAL: int = 50
    RATE_LIMIT_PER_CHANNEL: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
    )

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def parse_environment(cls, value: str | Environment) -> Environment:
        """Parse environment string to enum."""
        if isinstance(value, Environment):
            return value
        if value.upper() in ("DEV", "DEVELOPMENT"):
            return Environment.DEV
        if value.upper() in ("STAGE", "STAGING"):
            return Environment.DEV
        if value.upper() in ("PROD", "PRODUCTION"):
            return Environment.PROD
        valid_values = ["dev", "development", "staging", "prod", "production"]
        raise ValueError(f"ENVIRONMENT must be one of: {valid_values}")

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == Environment.DEV

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == Environment.PROD


# Global settings instance
_settings: Settings | None = None
_settings_lock = Lock()


def get_settings() -> Settings:
    """
    Get the singleton Settings instance.

    Returns:
        Settings: The application settings instance.
    """
    global _settings
    if _settings is None:
        with _settings_lock:
            if _settings is None:
                _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the singleton Settings instance.

    Intended for use in tests only. Clears the cached settings so the
    next call to ``get_settings()`` creates a fresh instance.
    """
    global _settings
    with _settings_lock:
        _settings = None
