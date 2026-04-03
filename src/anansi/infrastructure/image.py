"""
Image infrastructure — Vyro AI (reference image for panel continuity).
"""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx

from anansi.config import get_settings

logger = logging.getLogger(__name__)

VYRO_ENDPOINT = "https://api.vyro.ai/v2/image/generations"


async def generate_image(
    prompt: str,
    *,
    reference_image_url: str | None = None,
    style: str = "cartoon",
    aspect_ratio: str = "1:1",
) -> str:
    """
    Call Vyro image generation and return the resulting image URL.

    Args:
        prompt: Full prompt text.
        reference_image_url: Optional URL of the previous panel for consistency.
        style: Vyro style preset.
        aspect_ratio: Aspect ratio string accepted by the API.
    """
    settings = get_settings()
    api_key = settings.bfl_api_key
    if not api_key:
        raise RuntimeError("BFL_API_KEY not set")

    data: dict[str, Any] = {
        "prompt": prompt,
        "style": style,
        "aspect_ratio": aspect_ratio,
    }
    if reference_image_url:
        data["reference_image_url"] = reference_image_url

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(VYRO_ENDPOINT, data=data, headers=headers)
        resp.raise_for_status()
        body = cast(dict[str, Any], resp.json())
        return cast(str, body["data"]["image_url"])
