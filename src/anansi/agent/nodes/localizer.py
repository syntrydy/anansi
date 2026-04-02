from anansi.core.models.context import CountryData
from anansi.core.exceptions import CountryNotFoundError, DataLoadError
from anansi.core.constants import DATA_DIR, SUPPORTED_COUNTRIES
import json


def gather_context(country: str) -> CountryData:
    """
    Node 2 - Localizer
    Fetches cultural context from the MCP data layer.

    Args:
        country: Country name (Title-Case)

    Returns:
        CountryData object
    """
    if country not in SUPPORTED_COUNTRIES:
        raise CountryNotFoundError(country, list(SUPPORTED_COUNTRIES))

    path = DATA_DIR / f"{country}.json"
    if not path.exists():
        raise DataLoadError(path, "File not found")

    try:
        data = json.loads(path.read_text())
        return CountryData(**data)
    except Exception as e:
        raise DataLoadError(path, str(e))