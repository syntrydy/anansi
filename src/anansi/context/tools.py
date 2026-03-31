"""
MCP tool definitions for the Anansi cultural context server.

Tools are registered against a FastMCP instance via register_tools().
This pattern keeps the mcp instance in server.py (avoiding circular imports)
while making tools independently testable by injecting a test repository.

All tools catch CountryNotFoundError and surface it as a structured error
response rather than raising — the LLM caller receives a useful message.
"""

from fastmcp import FastMCP
from pydantic import BaseModel

from anansi.core.exceptions import CountryNotFoundError
from anansi.context.repository import ContextRepository


# ---------------------------------------------------------------------------
# MCP return models (MCP-layer concerns, distinct from core CountryData)
# ---------------------------------------------------------------------------


class NamesResult(BaseModel):
    male: list[str]
    female: list[str]
    error: str | None = None


class PlacesResult(BaseModel):
    cities: list[str]
    rivers: list[str]
    landmarks: list[str]
    error: str | None = None


class CultureResult(BaseModel):
    food: list[str]
    clothing: list[str]
    housing: list[str]
    transport: list[str]
    animals: list[str]
    art_style_cues: str
    error: str | None = None


class LanguageResult(BaseModel):
    official: str
    local: list[str]
    tts_code: str
    error: str | None = None


class AvoidsResult(BaseModel):
    avoids: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP, repo: ContextRepository) -> None:
    """Register all 5 cultural context tools onto *mcp* using *repo* as data source."""

    @mcp.tool()
    def get_names(country: str) -> NamesResult:
        """Return culturally accurate male and female given names for an African country.

        Args:
            country: The African country name (e.g. "Kenya", "Nigeria").

        Returns:
            NamesResult with male and female name lists, or an error message.
        """
        try:
            data = repo.get(country)
        except CountryNotFoundError as exc:
            return NamesResult(male=[], female=[], error=str(exc))
        return NamesResult(male=data.names.male, female=data.names.female)

    @mcp.tool()
    def get_places(country: str) -> PlacesResult:
        """Return cities, rivers, and landmarks for an African country.

        Args:
            country: The African country name (e.g. "Kenya", "Nigeria").

        Returns:
            PlacesResult with geographic location lists, or an error message.
        """
        try:
            data = repo.get(country)
        except CountryNotFoundError as exc:
            return PlacesResult(cities=[], rivers=[], landmarks=[], error=str(exc))
        return PlacesResult(
            cities=data.places.cities,
            rivers=data.places.rivers,
            landmarks=data.places.landmarks,
        )

    @mcp.tool()
    def get_culture(country: str) -> CultureResult:
        """Return cultural elements for an African country: food, clothing, housing,
        transport, animals, and a short visual art-style cue for image prompts.

        Args:
            country: The African country name (e.g. "Kenya", "Nigeria").

        Returns:
            CultureResult with cultural element lists and art_style_cues,
            or an error message.
        """
        try:
            data = repo.get(country)
        except CountryNotFoundError as exc:
            return CultureResult(
                food=[], clothing=[], housing=[], transport=[],
                animals=[], art_style_cues="", error=str(exc),
            )
        return CultureResult(
            food=data.culture.food,
            clothing=data.culture.clothing,
            housing=data.culture.housing,
            transport=data.culture.transport,
            animals=data.culture.animals,
            art_style_cues=data.art_style_cues,
        )

    @mcp.tool()
    def get_language(country: str) -> LanguageResult:
        """Return language information for an African country, including the
        official language, locally spoken languages, and the Google Cloud TTS
        BCP-47 language tag.

        Args:
            country: The African country name (e.g. "Kenya", "Nigeria").

        Returns:
            LanguageResult with language details, or an error message.
        """
        try:
            data = repo.get(country)
        except CountryNotFoundError as exc:
            return LanguageResult(official="", local=[], tts_code="", error=str(exc))
        return LanguageResult(
            official=data.languages.official,
            local=data.languages.local,
            tts_code=data.languages.tts_code,
        )

    @mcp.tool()
    def get_avoids(country: str) -> AvoidsResult:
        """Return a list of visual and textual elements to exclude from
        AI-generated images for an African country.  These are things that are
        geographically or culturally inaccurate (e.g. snow in tropical Kenya,
        dollar bills, oak trees).

        Args:
            country: The African country name (e.g. "Kenya", "Nigeria").

        Returns:
            AvoidsResult with the avoidance list, or an error message.
        """
        try:
            data = repo.get(country)
        except CountryNotFoundError as exc:
            return AvoidsResult(avoids=[], error=str(exc))
        return AvoidsResult(avoids=data.avoids)
