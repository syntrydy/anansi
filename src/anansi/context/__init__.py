"""
Context module — FastMCP cultural context server and repository.

Public surface:
    mcp        — FastMCP server instance (importable for in-process testing)
    repository — ContextRepository singleton
"""

from anansi.context.repository import repository
from anansi.context.server import mcp

__all__ = ["mcp", "repository"]
