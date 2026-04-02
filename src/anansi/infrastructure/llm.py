"""
LLM infrastructure — Anthropic (cloud) or Ollama (local) chat models.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import SecretStr

from anansi.config import get_settings

logger = logging.getLogger(__name__)


def get_llm() -> Any | None:
    """
    Return a LangChain chat model, or ``None`` if no provider is configured.

    Uses ``USE_LOCAL`` / Ollama when enabled, otherwise Anthropic when
    ``ANTHROPIC_API_KEY`` is set.
    """
    settings = get_settings()
    if settings.use_local_llm:
        try:
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_url,
            )
        except Exception as exc:
            logger.warning("Ollama LLM unavailable: %s", exc)
            return None

    if not settings.anthropic_api_key:
        return None

    try:
        from langchain_anthropic import ChatAnthropic

        # Pydantic model init is over-strict under mypy for optional chat fields.
        return ChatAnthropic(
            model_name=settings.anthropic_model,
            api_key=SecretStr(settings.anthropic_api_key),
        )  # type: ignore[call-arg]
    except Exception as exc:
        logger.warning("Anthropic LLM unavailable: %s", exc)
        return None
