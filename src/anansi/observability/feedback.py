"""Log teacher feedback to Langfuse as a score event."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _hash_input(data: dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def log_feedback(
    *,
    rating: str,
    comment: str,
    result: dict[str, Any],
    last_input: dict[str, Any],
) -> None:
    """Log teacher feedback to Langfuse. Silently degrades if Langfuse is absent."""
    try:
        from anansi.infrastructure.observability import get_langfuse_handler

        lf = get_langfuse_handler()
        if lf is None:
            logger.info("Feedback (no Langfuse): rating=%s comment=%r", rating, comment)
            return

        score_value = 1.0 if rating == "positive" else 0.0
        trace_id = (result.get("trace_id") or "") or _hash_input(last_input)

        try:
            lf.score(
                trace_id=trace_id,
                name="teacher_feedback",
                value=score_value,
                comment=comment or None,
                data_type="NUMERIC",
            )
        except Exception:
            lf.create_event(
                name="teacher_feedback",
                metadata={
                    "rating": rating,
                    "comment": comment,
                    "topic": last_input.get("topic", ""),
                    "country": last_input.get("country", ""),
                    "grade": last_input.get("grade", ""),
                },
            )

        logger.info("Teacher feedback logged: rating=%s", rating)
    except Exception as exc:
        logger.warning("Failed to log feedback: %s", exc)
