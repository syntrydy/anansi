"""
Node 4 - Cartoon Generator (Replicate / FLUX Schnell).
Generates one image per panel in parallel, all sharing the same seed and
character anchor for visual consistency across the comic strip.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from anansi.core.constants import MAX_PANELS
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.script import PanelScript
from anansi.infrastructure.image import generate_image
from anansi.observability.langfuse_pipeline import trace_panel_observation

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
_RATE_LIMIT_BACKOFF = 15   # fallback wait after a 429
_INTER_PANEL_DELAY = 11    # seconds between panel requests (stay under 6/min)


def _is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc) or "throttled" in str(exc).lower()


def _parse_retry_after(exc: Exception) -> int:
    """Extract 'resets in ~Xs' from a Replicate 429 message, with a 3s buffer."""
    match = re.search(r"resets in ~?(\d+)s", str(exc))
    if match:
        return int(match.group(1)) + 3
    return _RATE_LIMIT_BACKOFF


def _build_character_anchor(context_pack: dict) -> str:
    """Build a stable character/visual identity block from CountryData."""
    from anansi.core.models.context import CountryData
    ctx = CountryData.model_validate(context_pack)
    male   = ctx.names.male[0]   if ctx.names.male   else "a boy"
    female = ctx.names.female[0] if ctx.names.female else "a girl"
    clothing = ", ".join(ctx.culture.clothing[:3]) if ctx.culture.clothing else ""
    art_cues = ctx.art_style_cues or ""
    parts = [f"{male} (boy) and {female} (girl)"]
    if clothing:
        parts.append(f"wearing {clothing}")
    if art_cues:
        parts.append(art_cues)
    return ", ".join(parts)


def _extract_scene_content(script: PanelScript) -> str:
    """Extract just the visual scene description from a scriptor-generated prompt.

    The scriptor wraps scene content in one of two forms:
      Panel 1:  "Characters: <desc>. Scene: <scene content>. Do not show: ..."
      Panel 2+: "Continuing the same characters. Scene: <scene content>. Do not show: ..."

    We want only <scene content> — the character header and avoids suffix
    are both applied at the per-panel prompt level.
    """
    raw = script.prompt.strip()
    if not raw:
        return script.caption

    # Strip trailing "Do not show: ..." clause
    avoid_idx = raw.lower().rfind("do not show:")
    if avoid_idx >= 0:
        raw = raw[:avoid_idx].strip().rstrip(".")

    # Extract content after "Scene:" marker (present in both scriptor forms)
    scene_idx = raw.lower().find("scene:")
    if scene_idx >= 0:
        return raw[scene_idx + len("scene:"):].strip().rstrip(".")

    # No "Scene:" marker — strip "Continuing the same characters." prefix if present
    if raw.lower().startswith("continuing the same characters"):
        dot = raw.find(".")
        if dot >= 0:
            raw = raw[dot + 1:].strip()

    return raw or script.caption


def _build_panel_prompt(
    script: PanelScript,
    n_total: int,
    char_desc: str,
    avoids: str,
) -> str:
    """Build the FLUX prompt for a single panel."""
    scene = _extract_scene_content(script)
    prompt = (
        f"Educational cartoon illustration, panel {script.panel_number} of {n_total}. "
        f"{scene}. "
        f"Characters: {char_desc}. "
        f"Flat cartoon style, bright warm colors, clean linework, classroom-friendly."
    )
    if avoids:
        prompt += f" Do not show: {avoids}."
    return prompt


async def _generate_one_panel(
    script: PanelScript,
    n_total: int,
    char_desc: str,
    avoids: str,
    aspect_ratio: str,
    seed: int | None,
    max_retries: int,
) -> GeneratedImage:
    """Generate the image for a single panel with retries."""
    prompt = _build_panel_prompt(script, n_total, char_desc, avoids)
    t0 = time.perf_counter()
    success = False
    url = ""

    for attempt in range(max_retries + 1):
        try:
            url = await generate_image(prompt, aspect_ratio=aspect_ratio, seed=seed)
            success = True
            break
        except Exception as exc:
            logger.warning(
                "Panel %s image generation failed (attempt %s): %s",
                script.panel_number, attempt + 1, exc,
            )
            if attempt < max_retries:
                delay = _parse_retry_after(exc) if _is_rate_limit(exc) else 2
                logger.info("Panel %s: waiting %ss before retry…", script.panel_number, delay)
                await asyncio.sleep(delay)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    trace_panel_observation(
        kind="image",
        panel_number=script.panel_number,
        duration_ms=elapsed_ms,
        success=success,
        extra={"attempts": attempt + 1},
    )

    return GeneratedImage(
        panel_number=script.panel_number,
        url=url,
        caption=script.caption,
    )


async def generate_cartoon_panels(
    scripts: list[PanelScript],
    country: str,
    audience: str = "general",
    language: str = "English",
    aspect_ratio: str = "1:1",
    max_retries: int = MAX_RETRIES,
    skip_panel_numbers: set[int] | None = None,
    context_pack: dict | None = None,
    seed: int | None = None,
) -> list[GeneratedImage]:
    """
    Generate one image per panel sequentially via Replicate (FLUX Schnell).

    Requests are sent one at a time with an inter-panel delay to respect
    Replicate's burst=1 rate limit (6 req/min on free tier). All panels share
    the same seed and character anchor for visual consistency. Returns one
    GeneratedImage per active panel plus a panel_number=0 storyboard entry.
    """
    skip = skip_panel_numbers or set()
    active = [s for s in scripts[:MAX_PANELS] if s.panel_number not in skip]

    if not active:
        return []

    # Build shared character description and avoids from context pack
    if context_pack:
        from anansi.core.models.context import CountryData
        ctx = CountryData.model_validate(context_pack)
        char_desc = _build_character_anchor(context_pack)
        avoids = ", ".join(ctx.avoids) if ctx.avoids else ""
    else:
        char_desc = "African children"
        avoids = ""

    n_total = len(active)

    # Generate panels sequentially to respect Replicate's burst=1 rate limit.
    # A small delay between requests keeps throughput under 6 req/min.
    panel_images: list[GeneratedImage] = []
    for i, script in enumerate(active):
        img = await _generate_one_panel(
            script, n_total, char_desc, avoids, aspect_ratio, seed, max_retries
        )
        panel_images.append(img)
        if i < len(active) - 1:
            await asyncio.sleep(_INTER_PANEL_DELAY)

    # Use the first successfully generated image as the storyboard cover (panel_number=0)
    first_url = next((img.url for img in panel_images if img.url), "")
    storyboard = GeneratedImage(
        panel_number=0,
        url=first_url,
        caption=f"Storyboard — {n_total} panels",
    )

    return [storyboard, *panel_images]
