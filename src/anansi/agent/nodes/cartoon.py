"""
Node 4 - Cartoon Generator (Vyro AI via infrastructure.image).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from anansi.agent.nodes.localizer import gather_context
from anansi.core.constants import MAX_PANELS
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.script import PanelScript
from anansi.infrastructure.image import generate_image
from anansi.observability.langfuse_pipeline import trace_panel_observation

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


class CartoonPrompt(BaseModel):
    caption: str
    dialogue: str
    narration: str
    context_cues: list[str] = Field(default_factory=list)
    avoids: list[str] = Field(default_factory=list)
    audience: str = "general"
    panel_number: int
    prompt_text: str


def _build_prompt_text(prompt: CartoonPrompt) -> str:
    cues = " ".join(prompt.context_cues)
    avoids = ", ".join(f"avoid {a}" for a in prompt.avoids)
    return (
        f"Panel {prompt.panel_number}: {prompt.caption}. "
        f"{prompt.dialogue}. {prompt.narration}. "
        f"Cues: {cues}. {avoids}. Audience: {prompt.audience}."
    )


async def _prefetch_reference_url(url: str) -> None:
    """Warm HTTP connection / CDN for the reference image used on panels 2+."""
    u = (url or "").strip()
    if not u.startswith("http"):
        return
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            await client.get(u)
    except Exception:
        pass


async def generate_cartoon_panels(
    scripts: list[PanelScript],
    country: str,
    audience: str = "general",
    max_retries: int = MAX_RETRIES,
    skip_panel_numbers: set[int] | None = None,
) -> list[GeneratedImage]:
    """
    Generate cartoon panels for each script using Vyro (``generate_image``).

    Panels in ``skip_panel_numbers`` skip the API (e.g. safety-blocked).
    """
    skip = skip_panel_numbers or set()
    context_pack = gather_context(country)
    work: list[tuple[PanelScript, CartoonPrompt]] = []

    for script in scripts[:MAX_PANELS]:
        prompt = CartoonPrompt(
            caption=script.caption,
            dialogue=script.dialogue,
            narration=script.narration,
            context_cues=getattr(context_pack, "visual_cues", []),
            avoids=getattr(context_pack, "avoids", []),
            audience=audience,
            panel_number=script.panel_number,
            prompt_text="",
        )
        prompt.prompt_text = _build_prompt_text(prompt)
        work.append((script, prompt))

    results: list[GeneratedImage] = []
    reference_image_url: Optional[str] = None

    for script, prompt in work:
        pn = script.panel_number
        if pn in skip:
            results.append(
                GeneratedImage(
                    panel_number=pn,
                    url="",
                    caption=script.caption,
                    dialogue=script.dialogue,
                    narration=script.narration,
                )
            )
            trace_panel_observation(
                kind="image",
                panel_number=pn,
                duration_ms=0.0,
                success=False,
                extra={"skipped_safety": True},
            )
            continue

        success = False
        t0 = time.perf_counter()
        for attempt in range(max_retries + 1):
            try:
                ref_url = reference_image_url
                if ref_url:
                    await _prefetch_reference_url(ref_url)
                image_url = await generate_image(
                    prompt.prompt_text,
                    reference_image_url=ref_url,
                )

                results.append(
                    GeneratedImage(
                        panel_number=pn,
                        url=image_url,
                        caption=prompt.caption,
                        dialogue=prompt.dialogue,
                        narration=prompt.narration,
                    )
                )
                reference_image_url = image_url
                success = True
                break
            except Exception as exc:
                logger.warning(
                    "Panel %s generation failed (attempt %s): %s",
                    pn,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(1)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if not success:
            logger.error("Panel %s ultimately failed", pn)
            results.append(
                GeneratedImage(
                    panel_number=pn,
                    url="",
                    caption=script.caption,
                    dialogue=script.dialogue,
                    narration=script.narration,
                )
            )
        trace_panel_observation(
            kind="image",
            panel_number=pn,
            duration_ms=elapsed_ms,
            success=success,
            extra={"attempts": max_retries + 1},
        )

    return results
