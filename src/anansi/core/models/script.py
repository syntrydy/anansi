from pydantic import BaseModel


class PanelScript(BaseModel):
    """Per-panel script: text and image prompt for one cartoon panel."""

    panel_number: int
    panel_id: str = ""
    caption: str
    dialogue: str
    prompt: str
    narration: str
