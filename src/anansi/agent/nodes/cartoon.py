"""
Node 4 - Cartoon Generator
Generates cartoon panels based on the panel scripts, 
audience, and context pack using the Flux Kontext Pro API.
"""

from typing import List
import os
import time
import logging
import asyncio

import httpx
from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript
from anansi.core.models.cartoon import GeneratedImage
from anansi.agent.nodes.localizer import gather_context
from anansi.core.constants import MAX_PANELS

logger = logging.getLogger(__name__)

FLUX_ENDPOINT = "https://api.freepik.com/v1/ai/text-to-image/flux-kontext-pro"
FLUX_STATUS_ENDPOINT = "https://api.freepik.com/v1/ai/text-to-image/flux-kontext-pro/{task_id}"
MAX_RETRIES = 1

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
    api_key = os.getenv("BFL_API_KEY")
    if not api_key:
        raise RuntimeError("BFL_API_KEY not set")

    payload = {"prompt": prompt_text, "input_image": reference_url}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FLUX_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["data"]["task_id"]

async def _poll_flux_result(task_id: str, timeout: float = 30.0, interval: float = 1.5) -> str:
    api_key = os.getenv("BFL_API_KEY")
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
                return data["result"]["sample"]
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

    context_pack = gather_context(country)
    prompts: List[CartoonPrompt] = []

    for i, script in enumerate(scripts[:MAX_PANELS]):
        prompt = CartoonPrompt(
            caption=script.caption,
            dialogue=script.dialogue,
            narration=script.narration,
            context_cues=getattr(context_pack, "visual_cues", []),
            avoids=getattr(context_pack, "avoids", []),
            audience=audience,
            panel_number=i + 1,
            prompt_text=""
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