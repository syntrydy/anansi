"""Final package returned to the UI and export paths."""

from typing import Any

from pydantic import BaseModel, Field

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.storyboard import Scene


class PanelOutput(BaseModel):
    """One panel as shown in the UI (script + media + safety)."""

    panel_number: int
    panel_id: str = ""
    caption: str = ""
    dialogue: str = ""
    narration: str = ""
    image_url: str = ""
    audio_url: str = ""
    audio_error: str | None = None
    safe: bool = True
    safety_reason: str | None = None


class OutputPackage(BaseModel):
    """Aggregated lesson output."""

    storyboard_image_url: str = ""  # single comic-strip image covering all panels
    scenes: list[Scene] = Field(default_factory=list)
    images: list[GeneratedImage] = Field(default_factory=list)
    audios: list[GeneratedAudio] = Field(default_factory=list)
    panels: list[PanelOutput] = Field(default_factory=list)
    safety_results: list[dict[str, Any]] = Field(default_factory=list)
    teacher_guide: str = ""
