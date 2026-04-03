"""Panel-level script produced by the scriptor node."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PanelScript(BaseModel):
    """One panel's text and prompts, aligned by ``panel_number`` with images/audio."""

    panel_number: int = Field(..., ge=1, description="1-based index matching image/audio")
    panel_id: str = Field(default="", description="Stable id, often scene_id")
    caption: str
    dialogue: str          # Formatted as "Name: line.  Name2: line." for compatibility
    prompt: str            # Image generation prompt (field name kept for cartoon.py)
    narration: str         # TTS text (field name kept for narrator.py)


class ScriptOutput(BaseModel):
    """Structured output returned by N3 (Claude Haiku via with_structured_output)."""

    panels: list[PanelScript] = Field(description="One PanelScript per scene")
    full_narration: str = Field(
        default="",
        description="Combined narration text for all panels in sequence",
    )
