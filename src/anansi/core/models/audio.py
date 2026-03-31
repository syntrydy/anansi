from pydantic import BaseModel

class GeneratedAudio(BaseModel):
    audio_url: str
    duration_seconds: float