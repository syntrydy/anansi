"""
Node 4 - Cartoon Generator
Generates cartoon panels based on the panel scripts, 
audience, and context pack using the Flux Kontext Pro API.
"""

from typing import Any, List, cast
import asyncio
import logging
import os
import time

import httpx
from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript
from anansi.core.models.cartoon import GeneratedImage
from anansi.agent.nodes.localizer import gather_context
from anansi.config import get_settings
from anansi.core.constants import MAX_PANELS

logger = logging.getLogger(__name__)

FLUX_ENDPOINT = "https://api.freepik.com/v1/ai/text-to-image/flux-kontext-pro"
FLUX_STATUS_ENDPOINT = "https://api.freepik.com/v1/ai/text-to-image/flux-kontext-pro/{task_id}"
MAX_RETRIES = 1


def _mock_generated_images(scripts: List[PanelScript]) -> List[GeneratedImage]:
    """Placeholder panels when ``ANANSI_MOCK_PIPELINE`` is set (tests / local dev)."""
    return [
        GeneratedImage(
            panel_number=s.panel_number,
            url=f"https://example.invalid/mock/panel-{s.panel_number}.png",
            caption=s.caption,
            dialogue=s.dialogue,
            narration=s.narration,
        )
        for s in scripts[:MAX_PANELS]
    ]


class CartoonPrompt(BaseModel):
    caption: str
    dialogue: str
    narration: str
    context_cues: List[str] = Field(default_factory=list)
    avoids: List[str] = Field(default_factory=list)
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

async def _submit_flux_task(prompt_text: str, reference_url: str | None) -> str:
    api_key = get_settings().bfl_api_key
    if not api_key:
        raise RuntimeError("BFL_API_KEY not set")

    payload = {"prompt": prompt_text, "input_image": reference_url}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FLUX_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        body = cast(dict[str, Any], resp.json())
        return cast(str, body["data"]["task_id"])

async def _poll_flux_result(task_id: str, timeout: float = 30.0, interval: float = 1.5) -> str:
    api_key = get_settings().bfl_api_key
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    status_url = FLUX_STATUS_ENDPOINT.format(task_id=task_id)

    end_time = time.time() + timeout
    async with httpx.AsyncClient(timeout=20) as client:
        while time.time() < end_time:
            resp = await client.get(status_url, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            status = data.get("status")
            if status == "SUCCESS":
                return cast(str, data["result"]["sample"])
            elif status in ("FAILED", "ERROR"):
                raise RuntimeError(f"Flux generation failed for task {task_id}")
            await asyncio.sleep(interval)
        raise TimeoutError(f"Flux task {task_id} did not complete in time")

async def generate_cartoon_panels(
    scripts: List[PanelScript],
    country: str,
    audience: str = "general",
    max_retries: int = MAX_RETRIES
) -> List[GeneratedImage]:
    """
    Generates cartoon panels for each script using contextual cues.
    
    Args:
        scripts: List of PanelScript objects.
        country: Country to fetch context pack for local cues.
        audience: Target audience, e.g., "kid", "adult", "professional".
        max_retries: Number of retries per panel on failure.
    
    Returns:
        List of GeneratedImage objects with URLs and metadata.
    """
    if os.getenv("ANANSI_MOCK_PIPELINE", "").lower() in ("1", "true", "yes"):
        return _mock_generated_images(scripts)

    context_pack = gather_context(country)
    prompts: List[CartoonPrompt] = []

    context_cues: List[str] = []
    if getattr(context_pack, "art_style_cues", None):
        context_cues = [context_pack.art_style_cues]

    for script in scripts[:MAX_PANELS]:
        prompt = CartoonPrompt(
            caption=script.caption,
            dialogue=script.dialogue,
            narration=script.narration,
            context_cues=context_cues,
            avoids=list(getattr(context_pack, "avoids", []) or []),
            audience=audience,
            panel_number=script.panel_number,
            prompt_text="",
        )
        prompt.prompt_text = _build_prompt_text(prompt)
        prompts.append(prompt)

    results: List[GeneratedImage] = []
    reference_image_url: str | None = None

    for prompt in prompts:
        success = False
        for attempt in range(max_retries + 1):
            try:
                # Use reference image for panel 2+
                ref_url = reference_image_url if prompt.panel_number > 1 else None
                task_id = await _submit_flux_task(prompt.prompt_text, ref_url)
                image_url = await _poll_flux_result(task_id)

                results.append(
                    GeneratedImage(
                        panel_number=prompt.panel_number,
                        url=image_url,
                        caption=prompt.caption,
                        dialogue=prompt.dialogue,
                        narration=prompt.narration
                    )
                )

                if prompt.panel_number == 1:
                    reference_image_url = image_url
                success = True
                break
            except Exception as exc:
                logger.warning(
                    f"Panel {prompt.panel_number} generation failed (attempt {attempt+1}): {exc}"
                )
                await asyncio.sleep(1)

        if not success:
            logger.error(f"Panel {prompt.panel_number} ultimately failed")
            # Optional: append nothing or raise; here we skip

    return results