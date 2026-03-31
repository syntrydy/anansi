"""
FastMCP cultural context server entry point.

Run as a module:
    uv run python -m anansi.context.server

Transport is controlled by the MCP_TRANSPORT environment variable:
    - "stdio"  (default) — used by LangGraph Node 2 via subprocess
    - "http"              — used for development and direct HTTP inspection

The module-level `mcp` instance is importable by tests via FastMCP's
in-process client without starting a real subprocess.
"""

import os

from fastmcp import FastMCP

from anansi.context.repository import repository
from anansi.context.tools import register_tools

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp: FastMCP = FastMCP(
    name="anansi-context",
    instructions=(
        "Cultural context server for Anansi African educational cartoons. "
        "Provides country-specific names, places, cultural elements, "
        "language codes, and visual avoidance lists for AI image generation. "
        "Supported countries: Kenya, Nigeria, Senegal, Ghana, Cameroon."
    ),
)

# Register all 5 tools against the mcp instance.
register_tools(mcp, repository)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the FastMCP server with the transport specified by MCP_TRANSPORT."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
