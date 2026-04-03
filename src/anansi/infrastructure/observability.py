"""
Observability infrastructure — Langfuse client (SDK v4) for pipeline tracing.

``get_langfuse_handler`` is the single entry point used by
``anansi.observability.langfuse_pipeline`` and may be extended with LangChain
callbacks when LLM calls are wired through LangChain.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_langfuse_handler() -> Any | None:
    """
    Return the Langfuse client used for traces and spans.

    In Langfuse v4 the primary API is :func:`langfuse.get_client`; there is no
    separate "handler" object for custom spans. This function is the integration
    boundary for the rest of Anansi.
    """
    try:
        from langfuse import get_client

        client = get_client()
        if client is None or not getattr(client, "tracing_enabled", True):
            return client
        return client
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse unavailable: %s", exc)
        return None


def get_langchain_callback_handler() -> Any | None:
    """
    Optional LangChain callback handler for ``LLM.invoke`` / ``ainvoke`` tracing.

    Returns ``None`` if Langfuse LangChain integration is not installed or keys
    are missing.
    """
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse LangChain callback unavailable: %s", exc)
        return None
