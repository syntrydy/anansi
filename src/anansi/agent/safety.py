"""
Node 7 — Panel safety: fast heuristics plus optional LLM review via ``get_llm``.

Results are cached by script + context fingerprint so identical scripts are
evaluated once per process.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.infrastructure.llm import get_llm
from anansi.observability.langfuse_pipeline import trace_panel_observation

logger = logging.getLogger(__name__)

AVOIDED_TERMS = (
    "violence",
    "nudity",
    "drugs",
    "abuse",
    "politics",
)

_SAFETY_CACHE: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
_SAFETY_CACHE_MAX = 128


def _contains_avoided_terms(text: str) -> bool:
    text_lower = text.lower()
    return any(term in text_lower for term in AVOIDED_TERMS)


def _context_phrases(context_pack: dict[str, Any]) -> list[str]:
    """Flatten nested CountryData-like dicts into searchable substrings."""
    phrases: list[str] = []
    culture = context_pack.get("culture")
    if isinstance(culture, dict):
        for value in culture.values():
            if isinstance(value, list):
                phrases.extend(str(x) for x in value)
    places = context_pack.get("places")
    if isinstance(places, dict):
        for value in places.values():
            if isinstance(value, list):
                phrases.extend(str(x) for x in value)
    names = context_pack.get("names")
    if isinstance(names, dict):
        for value in names.values():
            if isinstance(value, list):
                phrases.extend(str(x) for x in value)
    return [p for p in phrases if p.strip()]


def _contains_local_elements(text: str, context_pack: dict[str, Any]) -> bool:
    needles = [p.lower() for p in _context_phrases(context_pack)]
    if not needles:
        return True
    lowered = text.lower()
    return any(n in lowered for n in needles)


def validate_panel_script(
    panel: PanelScript,
    context_pack: dict[str, Any],
    audience: str = "general",  # reserved for future audience-specific rules
) -> str | None:
    """Heuristic gate: return a human-readable reason if unsafe; else ``None``."""
    for field in (panel.caption, panel.dialogue, panel.narration, panel.prompt):
        if _contains_avoided_terms(field):
            return "Contains disallowed terms."

    combined = f"{panel.caption}. {panel.dialogue}. {panel.narration}"
    if not _contains_local_elements(combined, context_pack):
        return "Missing local cultural elements in text."

    return None


async def _llm_second_opinion(
    llm: Any,
    panel: PanelScript,
    audience: str,
) -> str | None:
    """Optional async LLM pass after heuristics pass."""
    try:
        from langchain_core.messages import HumanMessage

        prompt = (
            f"Audience: {audience}. Review this educational panel for child-appropriate "
            "K-12 classroom use (no graphic violence, hate, sexual content, or illegal acts).\n"
            f"Caption: {panel.caption}\n"
            f"Dialogue: {panel.dialogue}\n"
            f"Narration: {panel.narration}\n"
            "Reply with exactly one line starting with SAFE or UNSAFE: brief reason."
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        text = (getattr(resp, "content", None) or str(resp)).strip()
        if text.upper().startswith("UNSAFE"):
            part = text.split(":", 1)[-1].strip() if ":" in text else ""
            return part or "LLM flagged content"
        return None
    except Exception as exc:
        logger.warning("LLM safety review failed: %s", exc)
        return None


async def _evaluate_panel_async(
    panel: PanelScript,
    context_pack: dict[str, Any],
    audience: str,
    llm: Any | None,
) -> dict[str, Any]:
    """Single panel: heuristics first, then at most one LLM call when configured."""
    reason = validate_panel_script(panel, context_pack, audience)
    pn = panel.panel_number
    if reason is None and llm is not None:
        llm_reason = await _llm_second_opinion(llm, panel, audience)
        if llm_reason:
            reason = f"LLM review: {llm_reason}"
    if reason:
        logger.warning("Panel %s blocked: %s", pn, reason)
        row = {"panel_number": pn, "safe": False, "reason": reason}
    else:
        row = {"panel_number": pn, "safe": True, "reason": None}
    trace_panel_observation(
        kind="safety",
        panel_number=pn,
        duration_ms=0.0,
        success=reason is None,
        extra={"flagged": reason is not None, "reason": reason},
    )
    return row


def _safety_cache_key(
    scripts: list[PanelScript],
    context_pack: dict[str, Any],
    audience: str,
) -> str:
    payload = json.dumps(
        [p.model_dump() for p in scripts],
        sort_keys=True,
        default=str,
    )
    ctx = json.dumps(context_pack, sort_keys=True, default=str)
    raw = f"{payload}|{ctx}|{audience}".encode()
    return hashlib.sha256(raw).hexdigest()


async def _evaluate_all_panels_async(
    scripts: list[PanelScript],
    context_pack: dict[str, Any],
    audience: str,
) -> list[dict[str, Any]]:
    llm = get_llm()
    results: list[dict[str, Any]] = []
    for panel in scripts:
        results.append(await _evaluate_panel_async(panel, context_pack, audience, llm))
    n_flagged = sum(1 for r in results if not r.get("safe", True))
    logger.info(
        "Safety evaluation: %s panels, %s flagged",
        len(results),
        n_flagged,
    )
    return results


async def run_safety_check(
    scripts: list[PanelScript],
    state: AnansiState,
    audience: str = "general",
) -> list[dict[str, Any]]:
    """One result dict per script (cached; LLM runs at most once per panel on cache miss)."""
    context_pack = state.get("context_pack") or {}
    if not isinstance(context_pack, dict):
        context_pack = {}
    key = _safety_cache_key(scripts, context_pack, audience)
    if key in _SAFETY_CACHE:
        _SAFETY_CACHE.move_to_end(key)
        logger.info("Safety cache hit fingerprint=%s", key[:16])
        return [dict(r) for r in _SAFETY_CACHE[key]]

    results = await _evaluate_all_panels_async(scripts, context_pack, audience)
    _SAFETY_CACHE[key] = results
    while len(_SAFETY_CACHE) > _SAFETY_CACHE_MAX:
        _SAFETY_CACHE.popitem(last=False)
    return [dict(r) for r in results]
