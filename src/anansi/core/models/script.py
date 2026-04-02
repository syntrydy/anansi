"""Panel-level script produced by the scriptor node."""

from pydantic import BaseModel, Field


class PanelScript(BaseModel):
    """One panel’s text and prompts, aligned by ``panel_number`` with images/audio."""

    panel_number: int = Field(..., ge=1, description="1-based index matching image/audio")
    panel_id: str = Field(default="", description="Stable id, often scene_id")
    caption: str
    dialogue: str
    prompt: str
    narration: str
