"""
Configuration module for Anansi.
Handles loading environment variables and configuring global settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bfl_api_key: str = Field(default="", validation_alias="BFL_API_KEY")


def get_settings() -> Settings:
    """
    Return settings from the current process environment.

    Instantiated per call so tests can change ``os.environ`` between cases.
    """
    return Settings()
