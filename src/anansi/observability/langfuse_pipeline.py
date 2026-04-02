"""
Langfuse telemetry for the lesson graph: node spans, per-panel metrics, flush.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
from contextlib import contextmanager
from typing import Any, Iterator

from anansi.core.models.state import AnansiState

logger = logging.getLogger(__name__)

_trace_state_var: contextvars.ContextVar[AnansiState | None] = contextvars.ContextVar(
    "anansi_pipeline_trace_state",
    default=None,
)


def set_pipeline_trace_state(state: AnansiState) -> contextvars.Token[AnansiState | None]:
    """Bind graph state for nested per-panel spans (cartoon / narrator)."""
    return _trace_state_var.set(state)


def reset_pipeline_trace_state(token: contextvars.Token[AnansiState | None]) -> None:
    _trace_state_var.reset(token)


def current_pipeline_trace_state() -> AnansiState | None:
    return _trace_state_var.get()


def compute_script_hash(state: AnansiState) -> str:
    """Stable fingerprint for scripts when present, else teacher fields."""
    scripts = state.get("panel_scripts")
    if scripts:
        raw = json.dumps(scripts, sort_keys=True, default=str).encode()
    else:
        payload = {
            "topic": state.get("topic", ""),
            "country": state.get("country", ""),
            "grade": state.get("grade", 0),
            "language": state.get("language", ""),
            "audience": state.get("audience", "general"),
        }
        raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def pipeline_trace_metadata(state: AnansiState, step_name: str) -> dict[str, Any]:
    """Metadata attached to every pipeline span."""
    return {
        "step_name": step_name,
        "country": state.get("country", ""),
        "audience": state.get("audience", "general"),
        "script_hash": compute_script_hash(state),
        "topic": (state.get("topic") or "")[:200],
    }


def _langfuse_client() -> Any:
    try:
        from anansi.infrastructure.observability import get_langfuse_handler

        return get_langfuse_handler()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Langfuse client unavailable: %s", exc)
        return None


@contextmanager
def trace_pipeline_node(
    step_name: str,
    state: AnansiState,
) -> Iterator[None]:
    """
    Context manager: Langfuse span with start / success / error, or no-op if disabled.
    """
    lf = _langfuse_client()
    if lf is None:
        yield
        return
    if not getattr(lf, "tracing_enabled", True):
        yield
        return
    meta = pipeline_trace_metadata(state, step_name)
    try:
        cm = lf.start_as_current_observation(
            name=f"anansi.{step_name}",
            as_type="span",
            metadata=meta,
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse span start failed (%s): %s", step_name, exc)
        yield
        return
    with cm:
        try:
            yield
        except Exception as exc:
            logger.error(
                "Pipeline node %r failed: %s",
                step_name,
                exc,
                extra={"script_hash": meta.get("script_hash"), "country": meta.get("country")},
            )
            raise


def trace_panel_observation(
    *,
    kind: str,
    panel_number: int,
    duration_ms: float,
    success: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a short-lived nested span for one panel (image or audio generation)."""
    state = current_pipeline_trace_state()
    if state is None:
        return
    lf = _langfuse_client()
    if lf is None or not getattr(lf, "tracing_enabled", True):
        return
    meta: dict[str, Any] = {
        **pipeline_trace_metadata(state, f"{kind}_panel"),
        "panel_number": panel_number,
        "duration_ms": round(duration_ms, 2),
        "success": success,
    }
    if extra:
        meta.update(extra)
    try:
        with lf.start_as_current_observation(
            name=f"anansi.{kind}.panel_{panel_number}",
            as_type="span",
            metadata=meta,
        ):
            pass
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse panel span failed: %s", exc)


def flush_langfuse() -> None:
    """Best-effort flush after a pipeline run."""
    lf = _langfuse_client()
    if lf is None:
        return
    try:
        lf.flush()
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse flush failed: %s", exc)
