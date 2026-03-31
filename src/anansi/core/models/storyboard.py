from pydantic import BaseModel
from typing import List
from anansi.core.models.script import PanelScript

class Scene(BaseModel):
    scene_id: str
    title: str
    description: str
    panels: List[PanelScript] = []