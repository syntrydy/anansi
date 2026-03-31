from pydantic import BaseModel

class GeneratedAudio(BaseModel):
    panel_number: int
    audio_url: str  
    duration_seconds: float 
    error: str | None = None