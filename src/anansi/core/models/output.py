from pydantic import BaseModel
from typing import List
from anansi.core.models.storyboard import Scene
from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage

class OutputPackage(BaseModel):
    scenes: List[Scene]
    audios: List[GeneratedAudio] = []
    images: List[GeneratedImage] = []
    teacher_guide: str