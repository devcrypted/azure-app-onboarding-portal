"""Core application infrastructure (settings, dependency anchors)."""

from functools import lru_cache

from .settings import AppSettings


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()
