"""
Image infrastructure — Replicate (FLUX Schnell, cartoon style).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import replicate

logger = logging.getLogger(__name__)

_MODEL = "black-forest-labs/flux-schnell"

_SUPPORTED_RATIOS = {"1:1", "16:9", "4:3", "9:16", "3:4"}
_DEFAULT_RATIO = "1:1"


def _ratio(aspect_ratio: str) -> str:
    return aspect_ratio if aspect_ratio in _SUPPORTED_RATIOS else _DEFAULT_RATIO


async def generate_image(
    prompt: str,
    *,
    reference_image_url: str | None = None,
    style: str = "cartoon",
    aspect_ratio: str = "1:1",
    seed: int | None = None,
) -> str:
    """
    Generate a cartoon-style image via Replicate (FLUX Schnell).
    Returns the URL of the generated image.
    """
    token = os.getenv("REPLICATE_API_TOKEN", "")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not set")

    styled_prompt = (
        f"Children's educational cartoon illustration, bright warm colors, "
        f"flat cartoon style, no text, no words, no letters, no labels inside image. {prompt}"
    )

    input_payload: dict[str, Any] = {
        "prompt": styled_prompt,
        "aspect_ratio": _ratio(aspect_ratio),
        "num_outputs": 1,
        "output_format": "webp",
        "output_quality": 85,
    }
    if seed is not None:
        input_payload["seed"] = seed

    client = replicate.Client(api_token=token)
    output = await client.async_run(_MODEL, input=input_payload)

    logger.info("Replicate raw output type=%s value=%r", type(output).__name__, output)

    # output may be a list, iterator, or single FileOutput — iterate safely.
    items = list(output) if output is not None else []
    if not items:
        raise RuntimeError("Replicate returned empty output")

    url = str(items[0])
    logger.info("Storyboard image URL: %s", url)
    return url
