from pydantic import BaseModel

class GeneratedImage(BaseModel):
    image_url: str
    description: str