"""
Configuration module for Anansi.
Handles loading environment variables and configuring global settings.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from anansi.core.constants import MODEL_OLLAMA_REASONING, MODEL_REASONING, MODEL_STANDARD


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    cerebras_api_key: str = Field(default="", validation_alias="CEREBRAS_API_KEY")
    cerebras_model: str = Field(default="llama3.1-8b", validation_alias="CEREBRAS_MODEL")
    cerebras_model_reasoning: str = Field(
        default="llama3.1-8b", validation_alias="CEREBRAS_MODEL_REASONING"
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    replicate_api_token: str = Field(default="", validation_alias="REPLICATE_API_TOKEN")
    anthropic_model: str = Field(
        default=MODEL_STANDARD,
        validation_alias="ANTHROPIC_MODEL",
    )
    anthropic_model_reasoning: str = Field(
        default=MODEL_REASONING,
        validation_alias="ANTHROPIC_MODEL_REASONING",
    )
    use_local_llm: bool = Field(default=False, validation_alias="USE_LOCAL")
    ollama_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_URL",
    )
    ollama_model: str = Field(default="llama3.2", validation_alias="OLLAMA_MODEL")
    ollama_model_reasoning: str = Field(
        default=MODEL_OLLAMA_REASONING,
        validation_alias="OLLAMA_MODEL_REASONING",
    )

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
