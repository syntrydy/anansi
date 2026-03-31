from pydantic import BaseModel

class PanelScript(BaseModel):
    panel_id: str
    caption: str
    dialogue: str
    prompt: str