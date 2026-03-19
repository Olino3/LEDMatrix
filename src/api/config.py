"""Application-level settings using pydantic-settings.

Reads environment variables with the ``LEDMATRIX_`` prefix and provides
typed, validated configuration for the FastAPI application layer.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings with env-var overrides (prefix ``LEDMATRIX_``)."""

    model_config = SettingsConfigDict(env_prefix="LEDMATRIX_")

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    json_logging: bool = False
    hot_reload: bool = False
    config_path: str = "config/config.json"
    secrets_path: str = "config/config_secrets.json"


@lru_cache
def get_settings() -> AppSettings:
    """Return a cached ``AppSettings`` instance."""
    return AppSettings()
