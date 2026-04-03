"""
Node 4 - Cartoon Generator (Replicate / FLUX Schnell).
Generates a single multi-panel comic strip image in one API call.
"""

from __future__ import annotations

import asyncio
import logging
import time

from anansi.core.constants import MAX_PANELS
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.script import PanelScript
from anansi.infrastructure.image import generate_image
from anansi.observability.langfuse_pipeline import trace_panel_observation

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_RATE_LIMIT_BACKOFF = 15  # seconds to wait after a 429


def _is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc) or "throttled" in str(exc).lower()


def _build_strip_prompt(
    scripts: list[PanelScript],
    country: str,
    audience: str,
    language: str,
) -> str:
    n = len(scripts)
    # Use only the caption (visual scene description) — no dialogue/narration text
    # to avoid FLUX trying to render unreadable in-image text.
    panels_desc = "  ".join(
        f"Scene {s.panel_number}: {s.caption}."
        for s in scripts
    )
    return (
        f"{n} illustrated scenes for {audience} children in {country}. "
        f"Pure visual storytelling, no text inside the image. "
        f"{panels_desc} "
        f"African characters, diverse representation, bright warm colors, "
        f"flat cartoon illustration, clean linework, classroom-friendly."
    )


async def generate_cartoon_panels(
    scripts: list[PanelScript],
    country: str,
    audience: str = "general",
    language: str = "English",
    aspect_ratio: str = "1:1",
    max_retries: int = MAX_RETRIES,
    skip_panel_numbers: set[int] | None = None,
) -> list[GeneratedImage]:
    """
    Generate a single comic-strip image covering all panels via one Replicate call.
    Returns a list with one GeneratedImage at panel_number=0.
    """
    skip = skip_panel_numbers or set()
    active = [s for s in scripts[:MAX_PANELS] if s.panel_number not in skip]

    if not active:
        return []

    prompt = _build_strip_prompt(active, country, audience, language)
    # Comic strips look better in landscape; use 16:9 regardless of per-panel ratio.
    strip_ratio = "16:9"

    t0 = time.perf_counter()
    success = False
    url = ""

    for attempt in range(max_retries + 1):
        try:
            url = await generate_image(prompt, aspect_ratio=strip_ratio)
            success = True
            break
        except Exception as exc:
            logger.warning("Comic strip generation failed (attempt %s): %s", attempt + 1, exc)
            if attempt < max_retries:
                delay = _RATE_LIMIT_BACKOFF if _is_rate_limit(exc) else 2
                logger.info("Waiting %ss before retry…", delay)
                await asyncio.sleep(delay)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    trace_panel_observation(
        kind="image",
        panel_number=0,
        duration_ms=elapsed_ms,
        success=success,
        extra={"attempts": attempt + 1, "panels_in_strip": len(active)},
    )

    return [
        GeneratedImage(
            panel_number=0,
            url=url,
            caption=f"Comic strip — {len(active)} panels",
        )
    ]
