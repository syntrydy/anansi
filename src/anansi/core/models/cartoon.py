"""Cartoon / image generation output models."""

from pydantic import BaseModel


class GeneratedImage(BaseModel):
    """One generated panel image and its script fields."""

    panel_number: int
    url: str
    caption: str = ""
    dialogue: str = ""
    narration: str = ""
