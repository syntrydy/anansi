"""
Integration tests for the FastMCP cultural context server.

Tests use FastMCP's in-process Client — no subprocess or network socket.
The `mcp` instance is imported directly from the server module, which also
triggers repository loading and tool registration.

Assertion strategy:
- result.structured_content  → dict access for simple field checks
- result.data.<field>        → attribute access when the type has known fields
- result.is_error            → must be False for all valid-country calls
"""

import re

import pytest
from fastmcp import Client

from anansi.context.server import mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BCP47_RE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")

ALL_COUNTRIES = ["Kenya", "Nigeria", "Senegal", "Ghana", "Cameroon"]


# ---------------------------------------------------------------------------
# get_names
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_names_kenya_returns_names() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_names", {"country": "Kenya"})
    assert not result.is_error
    data = result.structured_content
    assert isinstance(data["male"], list)
    assert isinstance(data["female"], list)
    assert len(data["male"]) >= 4
    assert len(data["female"]) >= 4


@pytest.mark.asyncio
@pytest.mark.parametrize("country", ALL_COUNTRIES)
async def test_get_names_all_countries(country: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_names", {"country": country})
    assert not result.is_error
    data = result.structured_content
    assert data["male"], f"{country}: male names list is empty"
    assert data["female"], f"{country}: female names list is empty"
    assert data.get("error") is None


# ---------------------------------------------------------------------------
# get_places
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_places_nigeria_has_cities_and_rivers() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_places", {"country": "Nigeria"})
    assert not result.is_error
    data = result.structured_content
    assert len(data["cities"]) >= 3
    assert len(data["rivers"]) >= 2
    assert len(data["landmarks"]) >= 3


@pytest.mark.asyncio
@pytest.mark.parametrize("country", ALL_COUNTRIES)
async def test_get_places_all_countries(country: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_places", {"country": country})
    assert not result.is_error
    data = result.structured_content
    assert data["cities"], f"{country}: cities list is empty"
    assert data["rivers"], f"{country}: rivers list is empty"
    assert data["landmarks"], f"{country}: landmarks list is empty"
    assert data.get("error") is None


# ---------------------------------------------------------------------------
# get_culture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_culture_senegal_has_all_sub_fields() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_culture", {"country": "Senegal"})
    assert not result.is_error
    data = result.structured_content
    for field in ("food", "clothing", "housing", "transport", "animals"):
        assert data[field], f"Senegal culture.{field} is empty"
    assert data["art_style_cues"].strip() != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("country", ALL_COUNTRIES)
async def test_get_culture_art_style_cues_populated(country: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_culture", {"country": country})
    assert not result.is_error
    data = result.structured_content
    assert data["art_style_cues"].strip() != "", (
        f"{country}: art_style_cues is empty"
    )
    assert data.get("error") is None


# ---------------------------------------------------------------------------
# get_language
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_language_ghana_bcp47_format() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_language", {"country": "Ghana"})
    assert not result.is_error
    data = result.structured_content
    assert BCP47_RE.match(data["tts_code"]), (
        f"tts_code '{data['tts_code']}' does not match BCP-47 pattern"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("country", ALL_COUNTRIES)
async def test_get_language_all_countries_tts_code_non_empty(country: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_language", {"country": country})
    assert not result.is_error
    data = result.structured_content
    assert data["tts_code"].strip() != "", f"{country}: tts_code is empty"
    assert data["official"].strip() != "", f"{country}: official language is empty"
    assert data.get("error") is None


# ---------------------------------------------------------------------------
# get_avoids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_avoids_cameroon_non_empty() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_avoids", {"country": "Cameroon"})
    assert not result.is_error
    data = result.structured_content
    assert len(data["avoids"]) >= 4
    assert data.get("error") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("country", ALL_COUNTRIES)
async def test_get_avoids_all_countries(country: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_avoids", {"country": country})
    assert not result.is_error
    data = result.structured_content
    assert data["avoids"], f"{country}: avoids list is empty"
    assert data.get("error") is None


# ---------------------------------------------------------------------------
# Unknown country — graceful error (no exception, structured error field)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool",
    ["get_names", "get_places", "get_culture", "get_language", "get_avoids"],
)
async def test_unknown_country_returns_error_not_exception(tool: str) -> None:
    """All tools must return a structured error for unsupported countries,
    not raise an unhandled exception that would crash the MCP server."""
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"country": "Antarctica"})
    # is_error may be True or False depending on FastMCP version; what matters
    # is that the call completes and the 'error' field in structured content is set.
    data = result.structured_content
    assert data.get("error") is not None, (
        f"Tool '{tool}' did not set an error field for unknown country"
    )


# ---------------------------------------------------------------------------
# Tool discovery — server exposes exactly 5 tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_exposes_five_tools() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "get_names",
        "get_places",
        "get_culture",
        "get_language",
        "get_avoids",
    }
