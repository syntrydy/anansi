"""
Custom exception hierarchy for the Anansi application.

All application-specific exceptions derive from AnansiError so callers
can catch the entire family with a single except clause when needed.
"""

from pathlib import Path


class AnansiError(Exception):
    """Base class for all Anansi application errors."""


class CountryNotFoundError(AnansiError):
    """Raised when a requested country has no context pack in the data directory."""

    def __init__(self, country: str, supported: list[str] | None = None) -> None:
        self.country = country
        self.supported = supported or []
        hint = (
            f"  Supported countries: {', '.join(sorted(self.supported))}"
            if self.supported
            else ""
        )
        super().__init__(
            f"No context pack found for country '{country}'.{hint}"
        )


class DataLoadError(AnansiError):
    """Raised when a context pack JSON file cannot be loaded or parsed."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load context pack '{path}': {reason}")
