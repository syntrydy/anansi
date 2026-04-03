"""
Configuration module for Anansi.
Handles loading environment variables and configuring global settings.
"""

from pydantic import Field, field_validator
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
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-haiku-20241022",
        validation_alias="ANTHROPIC_MODEL",
    )
    use_local_llm: bool = Field(default=False, validation_alias="USE_LOCAL")
    ollama_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_URL",
    )
    ollama_model: str = Field(default="llama3.2", validation_alias="OLLAMA_MODEL")

    @field_validator("use_local_llm", mode="before")
    @classmethod
    def _coerce_use_local(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return bool(value)


def get_settings() -> Settings:
    """
    Return settings from the current process environment.

    Instantiated per call so tests can change ``os.environ`` between cases.
    """
    return Settings()
