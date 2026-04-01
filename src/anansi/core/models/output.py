from pydantic import BaseModel

from anansi.core.models.storyboard import Scene
from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage


class PanelOutput(BaseModel):
    """Merged panel: script fields plus image and narration audio."""

    panel_number: int
    caption: str
    dialogue: str
    narration: str
    image_url: str
    audio_url: str
    audio_error: str | None = None


class OutputPackage(BaseModel):
    """End-of-pipeline teaching package."""

    scenes: list[Scene]
    images: list[GeneratedImage] = []
    audios: list[GeneratedAudio] = []
    panels: list[PanelOutput] = []
    teacher_guide: str = ""
