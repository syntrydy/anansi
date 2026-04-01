from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript


class Scene(BaseModel):
    """One storyboard beat (often one panel) from the concept analyzer."""

    panel_number: int
    description: str
    scene_id: str = ""
    title: str = ""
    panels: list[PanelScript] = Field(default_factory=list)
