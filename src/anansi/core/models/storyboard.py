"""Storyboard / scene models for N1 output and graph state."""

from __future__ import annotations

from pydantic import BaseModel, Field

from anansi.core.models.script import PanelScript


class Scene(BaseModel):
    # --- Existing fields (must not be renamed — used throughout graph state) ---
    scene_id: str
    title: str
    description: str
    panels: list[PanelScript] = Field(default_factory=list)

    # --- Spec fields added as optional with defaults so Scene(**old_dict) still works ---
    panel_number: int = Field(default=0, description="1-based sequence position")
    key_concept: str = Field(default="", description="Core learning concept for this panel")
    characters: list[str] = Field(
        default_factory=list,
        description="Character placeholders e.g. [CHILD_NAME]",
    )
    setting: str = Field(default="", description="Physical location for the scene")


class StoryboardOutput(BaseModel):
    """Structured output returned by N1 (Claude Sonnet via with_structured_output)."""

    title: str = Field(description="Lesson title")
    scenes: list[Scene] = Field(description="exactly 6 sequential visual scenes")
    total_panels: int = Field(description="Total number of panels (== len(scenes))")
