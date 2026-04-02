from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript


class Scene(BaseModel):
    scene_id: str
    title: str
    description: str
    panels: list[PanelScript] = Field(default_factory=list)