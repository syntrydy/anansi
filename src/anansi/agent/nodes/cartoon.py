"""
Node 4 - Cartoon Generator (Vyro AI)
Generates cartoon panels based on panel scripts, audience, and context using Vyro API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, cast

import httpx
from pydantic import BaseModel, Field

from anansi.agent.nodes.localizer import gather_context
from anansi.config import get_settings
from anansi.core.constants import MAX_PANELS
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.script import PanelScript

logger = logging.getLogger(__name__)

VYRO_ENDPOINT = "https://api.vyro.ai/v2/image/generations"
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


async def _generate_vyro_image(
    prompt_text: str, reference_url: Optional[str] = None
) -> str:
    """Send prompt to Vyro AI API and return image URL."""
    api_key = get_settings().bfl_api_key
    if not api_key:
        raise RuntimeError("BFL_API_KEY not set")

    data: dict[str, Any] = {
        "prompt": prompt_text,
        "style": "cartoon",
        "aspect_ratio": "1:1",
    }
    if reference_url:
        data["reference_image_url"] = reference_url

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(VYRO_ENDPOINT, data=data, headers=headers)
        resp.raise_for_status()
        body = cast(dict[str, Any], resp.json())
        return cast(str, body["data"]["image_url"])


async def generate_cartoon_panels(
    scripts: list[PanelScript],
    country: str,
    audience: str = "general",
    max_retries: int = MAX_RETRIES,
    skip_panel_numbers: set[int] | None = None,
) -> list[GeneratedImage]:
    """
    Generate cartoon panels for each script using Vyro AI.

    Panels whose numbers appear in ``skip_panel_numbers`` get empty ``url`` rows
    (no API call), e.g. when blocked by safety.
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
            continue

        success = False
        for attempt in range(max_retries + 1):
            try:
                ref_url = reference_image_url
                image_url = await _generate_vyro_image(prompt.prompt_text, ref_url)

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

    return results
