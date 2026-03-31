"""
Node 4 - Cartoon Generator
Generates cartoon panels based on the panel scripts, 
audience, and context pack using the FLUX/AI generator.
"""

from typing import List
from pydantic import BaseModel, Field
from anansi.core.models.script import PanelScript
from anansi.core.models.cartoon import GeneratedImage
from anansi.agent.nodes.localizer import gather_context  # MCP fetch
from anansi.core.constants import MAX_PANELS

class CartoonPrompt(BaseModel):
    """
    Structure for generating an image prompt for FLUX.
    """
    caption: str
    dialogue: str
    narration: str
    context_cues: List[str] = Field(default_factory=list)
    avoids: List[str] = Field(default_factory=list)
    audience: str = "general"  # kid, adult, professional
    panel_number: int

def generate_cartoon_panels(
    scripts: List[PanelScript],
    country: str,
    audience: str = "general"
) -> List[GeneratedImage]:
    """
    Generates cartoon panels for each script using contextual cues.
    
    Args:
        scripts: List of PanelScript objects.
        country: Country to fetch context pack for local cues.
        audience: Target audience, e.g., "kid", "adult", "professional".
    
    Returns:
        List of GeneratedImage objects.
    """

    # Step 1: Gather cultural context
    context_pack = gather_context(country)

    # Step 2: Build structured prompts
    prompts: List[CartoonPrompt] = []
    for idx, script in enumerate(scripts[:MAX_PANELS]):
        prompt = CartoonPrompt(
            caption=script.caption,
            dialogue=script.dialogue,
            narration=script.narration,
            context_cues=context_pack.visual_cues if hasattr(context_pack, "visual_cues") else [],
            avoids=context_pack.avoids if hasattr(context_pack, "avoids") else [],
            audience=audience,
            panel_number=idx + 1
        )
        prompts.append(prompt)

    # Step 3: Call AI image generator (FLUX/LLM)
    images: List[GeneratedImage] = []
    for prompt in prompts:
        # Placeholder for actual FLUX call
        # Replace with your image generation SDK/API call
        image_url = f"https://flux.ai/fake_image?panel={prompt.panel_number}"
        images.append(
            GeneratedImage(
                panel_number=prompt.panel_number,
                url=image_url,
                caption=prompt.caption,
                dialogue=prompt.dialogue,
                narration=prompt.narration
            )
        )

    return images