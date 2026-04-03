"""
Node 2 — Localizer.

Calls all 5 FastMCP cultural context tools via FastMCP's in-process client.
No separate MCP server process is required; the mcp instance is imported
directly from context.server and executed in-process.
"""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client

from anansi.context.server import mcp
from anansi.core.exceptions import CountryNotFoundError
from anansi.core.models.context import (
    CountryData,
    CultureData,
    LanguageInfo,
    NamesData,
    PlacesData,
)


def _parse(result) -> dict:
    """Extract the dict from a FastMCP tool result.

    Supports both the legacy list-of-blocks API and the newer
    ``CallToolResult`` object (which wraps blocks under ``.content``).
    """
    blocks = result.content if hasattr(result, "content") else result
    return json.loads(blocks[0].text)


async def gather_context(country: str) -> CountryData:
    """
    Call all 5 MCP tools in parallel and assemble a CountryData object.

    Args:
        country: Country name (case-insensitive).

    Raises:
        CountryNotFoundError: If the MCP tool returns an error for this country.
    """
    async with Client(mcp) as client:
        results = await asyncio.gather(
            client.call_tool("get_names", {"country": country}),
            client.call_tool("get_places", {"country": country}),
            client.call_tool("get_culture", {"country": country}),
            client.call_tool("get_language", {"country": country}),
            client.call_tool("get_avoids", {"country": country}),
        )

    names_r, places_r, culture_r, language_r, avoids_r = [_parse(r) for r in results]

    # Any tool that failed carries an "error" key
    for result in (names_r, places_r, culture_r, language_r, avoids_r):
        if result.get("error"):
            raise CountryNotFoundError(country, [])

    return CountryData(
        country=country,
        languages=LanguageInfo(
            official=language_r["official"],
            local=language_r["local"],
            tts_code=language_r["tts_code"],
        ),
        names=NamesData(
            male=names_r["male"],
            female=names_r["female"],
        ),
        places=PlacesData(
            cities=places_r["cities"],
            rivers=places_r["rivers"],
            landmarks=places_r["landmarks"],
        ),
        culture=CultureData(
            food=culture_r["food"],
            clothing=culture_r["clothing"],
            housing=culture_r["housing"],
            transport=culture_r["transport"],
            animals=culture_r["animals"],
        ),
        art_style_cues=culture_r["art_style_cues"],
        avoids=avoids_r["avoids"],
    )
