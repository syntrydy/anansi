"""
Node 7 — Heuristic safety check for panel scripts (no LLM).
"""

from __future__ import annotations

import logging
from typing import Any

from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState

logger = logging.getLogger(__name__)

AVOIDED_TERMS = (
    "violence",
    "nudity",
    "drugs",
    "abuse",
    "politics",
)


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
    audience: str = "general",
) -> str | None:
    """Return a human-readable reason if unsafe; otherwise ``None``."""
    for field in (panel.caption, panel.dialogue, panel.narration, panel.prompt):
        if _contains_avoided_terms(field):
            return "Contains disallowed terms."

    combined = f"{panel.caption}. {panel.dialogue}. {panel.narration}"
    if not _contains_local_elements(combined, context_pack):
        return "Missing local cultural elements in text."

    if audience.lower() == "kid":
        inappropriate = ("blood", "death", "war")
        if any(word in combined.lower() for word in inappropriate):
            return "Not age-appropriate for kids."

    return None


def run_safety_check(
    scripts: list[PanelScript],
    state: AnansiState,
    audience: str = "general",
) -> list[dict[str, Any]]:
    """One result dict per script, keyed by ``panel_number``."""
    context_pack = state.get("context_pack") or {}
    if not isinstance(context_pack, dict):
        context_pack = {}
    results: list[dict[str, Any]] = []
    for panel in scripts:
        reason = validate_panel_script(panel, context_pack, audience)
        pn = panel.panel_number
        if reason:
            logger.warning("Panel %s blocked: %s", pn, reason)
            results.append({"panel_number": pn, "safe": False, "reason": reason})
        else:
            results.append({"panel_number": pn, "safe": True, "reason": None})
    return results
