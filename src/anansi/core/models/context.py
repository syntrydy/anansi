"""
Pydantic models for cultural context data.

CountryData is the root model and mirrors the JSON schema in
context/data/schema.json exactly.  The MCP tool return models
(NamesResult, PlacesResult, etc.) live in context/tools.py because they
are MCP-layer concerns, not core data concerns.
"""

from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    official: str = Field(..., description="Official/primary language of the country")
    local: list[str] = Field(default_factory=list, description="Locally spoken languages")
    tts_code: str = Field(..., description="BCP-47 language tag for Google Cloud TTS")


class NamesData(BaseModel):
    male: list[str] = Field(default_factory=list, description="Culturally accurate male given names")
    female: list[str] = Field(default_factory=list, description="Culturally accurate female given names")


class PlacesData(BaseModel):
    cities: list[str] = Field(default_factory=list)
    rivers: list[str] = Field(default_factory=list)
    landmarks: list[str] = Field(default_factory=list)


class CultureData(BaseModel):
    food: list[str] = Field(default_factory=list)
    clothing: list[str] = Field(default_factory=list)
    housing: list[str] = Field(default_factory=list)
    transport: list[str] = Field(default_factory=list)
    animals: list[str] = Field(default_factory=list)


class CountryData(BaseModel):
    """Root model — one instance per country JSON file."""

    country: str = Field(..., description="Canonical country name (Title-Case)")
    languages: LanguageInfo
    names: NamesData
    places: PlacesData
    culture: CultureData
    art_style_cues: str = Field(
        ...,
        description="Short phrase describing the visual landscape for FLUX image prompts",
    )
    avoids: list[str] = Field(
        default_factory=list,
        description="Visual/textual elements to exclude from generated images",
    )
