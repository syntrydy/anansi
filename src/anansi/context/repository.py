"""
ContextRepository — loads and serves country cultural data from JSON packs.

Design decisions:
- All packs are loaded eagerly at instantiation (startup cost ~negligible,
  5 small JSON files totalling < 20 KB).
- Lookup is case-insensitive (normalised to lowercase) so callers do not
  need to worry about exact capitalisation.
- New country files are auto-discovered by globbing *.json in data_dir,
  excluding schema.json.  No code changes required when adding a country.
- The module-level `repository` singleton is the object imported by tools.py
  so the server starts up with one shared, pre-loaded instance.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from anansi.core.constants import DATA_DIR
from anansi.core.exceptions import CountryNotFoundError, DataLoadError
from anansi.core.models.context import CountryData


class ContextRepository:
    """In-memory store of country cultural data, loaded from JSON at init."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        # Maps normalised (lowercase) country name → CountryData
        self._data: dict[str, CountryData] = {}
        self._load_all(data_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_all(self, data_dir: Path) -> None:
        """Glob all *.json files in data_dir (except schema.json) and parse."""
        json_files = [
            p for p in data_dir.glob("*.json") if p.name != "schema.json"
        ]
        for path in json_files:
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        """Parse a single country JSON file into a CountryData model."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataLoadError(path, str(exc)) from exc

        try:
            pack = CountryData.model_validate(raw)
        except ValidationError as exc:
            raise DataLoadError(path, str(exc)) from exc

        key = pack.country.strip().lower()
        self._data[key] = pack

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, country: str) -> CountryData:
        """Return the CountryData for *country*.

        Args:
            country: Country name (case-insensitive).

        Raises:
            CountryNotFoundError: If no pack exists for the given country.
        """
        key = country.strip().lower()
        if key not in self._data:
            raise CountryNotFoundError(country, self.supported_countries)
        return self._data[key]

    @property
    def supported_countries(self) -> list[str]:
        """Return canonical country names for all loaded packs."""
        return [pack.country for pack in self._data.values()]

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, country: str) -> bool:
        return country.strip().lower() in self._data


# Module-level singleton — imported by context/tools.py and context/server.py.
repository: ContextRepository = ContextRepository()
