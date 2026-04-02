"""
Node 4 - Cartoon Generator (Vyro AI)
Generates cartoon panels based on panel scripts, audience, and context using Vyro API.
"""

from typing import Any, List, Optional, cast
import asyncio
import logging
import httpx
from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript
from anansi.core.models.cartoon import GeneratedImage
from anansi.agent.nodes.localizer import gather_context
from anansi.config import get_settings
from anansi.core.constants import MAX_PANELS

logger = logging.getLogger(__name__)

VYRO_ENDPOINT = "https://api.vyro.ai/v2/image/generations"
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


async def _generate_vyro_image(prompt_text: str, reference_url: Optional[str] = None) -> str:
    """
    Send prompt to Vyro AI API and return image URL.
    """
    api_key = get_settings().bfl_api_key
    if not api_key:
        raise RuntimeError("BFL_API_KEY not set")

    data = {
        "prompt": prompt_text,
        "style": "cartoon",
        "aspect_ratio": "1:1"
    }

    # Use reference image as seed for panel 2+
    if reference_url:
        data["reference_image_url"] = reference_url

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(VYRO_ENDPOINT, data=data, headers=headers)
        resp.raise_for_status()
        body = cast(dict[str, Any], resp.json())
        # Expect `body["data"]["image_url"]` according to Vyro API
        return cast(str, body["data"]["image_url"])


async def generate_cartoon_panels(
    scripts: List[PanelScript],
    country: str,
    audience: str = "general",
    max_retries: int = MAX_RETRIES
) -> List[GeneratedImage]:
    """
    Generate cartoon panels for each script using Vyro AI.

    Args:
        scripts: List of PanelScript objects.
        country: Country to fetch context pack for local cues.
        audience: Target audience, e.g., "kid", "adult".
        max_retries: Number of retries per panel on failure.

    Returns:
        List of GeneratedImage objects with URLs and metadata.
    """

    context_pack = gather_context(country)
    prompts: List[CartoonPrompt] = []

    # Build prompts
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
    reference_image_url: Optional[str] = None

    for prompt in prompts:
        success = False
        for attempt in range(max_retries + 1):
            try:
                ref_url = reference_image_url if prompt.panel_number > 1 else None
                image_url = await _generate_vyro_image(prompt.prompt_text, ref_url)

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

    return results