"""
Unit tests for ContextRepository.

These tests are isolated — they use the real JSON data files but do not
start any MCP server or network socket.
"""

import json
import pytest
from pathlib import Path

from anansi.context.repository import ContextRepository
from anansi.core.exceptions import CountryNotFoundError, DataLoadError
from anansi.core.models.context import CountryData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo() -> ContextRepository:
    """Return a freshly loaded ContextRepository from the real data directory."""
    return ContextRepository()


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    """Return a temporary directory pre-populated with a minimal valid JSON pack."""
    pack = {
        "country": "Testland",
        "languages": {"official": "Testish", "local": ["Testish"], "tts_code": "ts-TS"},
        "names": {"male": ["Alpha", "Beta"], "female": ["Gamma", "Delta"]},
        "places": {
            "cities": ["City A", "City B"],
            "rivers": ["River X"],
            "landmarks": ["Peak Y"],
        },
        "culture": {
            "food": ["dish1"],
            "clothing": ["cloth1"],
            "housing": ["house1"],
            "transport": ["bus1"],
            "animals": ["cat"],
        },
        "art_style_cues": "flat grassland",
        "avoids": ["snow"],
    }
    (tmp_path / "testland.json").write_text(json.dumps(pack), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------


def test_all_five_countries_load(repo: ContextRepository) -> None:
    assert len(repo) == 5


def test_supported_countries_contains_all_phase1(repo: ContextRepository) -> None:
    names = {c.lower() for c in repo.supported_countries}
    assert {"kenya", "nigeria", "senegal", "ghana", "cameroon"} == names


def test_kenya_loads_as_country_data(repo: ContextRepository) -> None:
    kenya = repo.get("Kenya")
    assert isinstance(kenya, CountryData)
    assert kenya.country == "Kenya"


# ---------------------------------------------------------------------------
# Case-insensitive lookup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", ["Kenya", "kenya", "KENYA", "kEnYa"])
def test_case_insensitive_lookup(repo: ContextRepository, variant: str) -> None:
    data = repo.get(variant)
    assert data.country == "Kenya"


# ---------------------------------------------------------------------------
# Content smoke tests (data populated, not empty)
# ---------------------------------------------------------------------------


def test_kenya_names_are_populated(repo: ContextRepository) -> None:
    kenya = repo.get("Kenya")
    assert len(kenya.names.male) >= 4
    assert len(kenya.names.female) >= 4


def test_nigeria_places_are_populated(repo: ContextRepository) -> None:
    nigeria = repo.get("Nigeria")
    assert len(nigeria.places.cities) >= 3
    assert len(nigeria.places.rivers) >= 2
    assert len(nigeria.places.landmarks) >= 3


def test_senegal_culture_food_populated(repo: ContextRepository) -> None:
    senegal = repo.get("Senegal")
    assert len(senegal.culture.food) >= 4


def test_ghana_avoids_populated(repo: ContextRepository) -> None:
    ghana = repo.get("Ghana")
    assert len(ghana.avoids) >= 4


def test_cameroon_art_style_cues_not_empty(repo: ContextRepository) -> None:
    cameroon = repo.get("Cameroon")
    assert cameroon.art_style_cues.strip() != ""


def test_all_tts_codes_non_empty(repo: ContextRepository) -> None:
    for country in repo.supported_countries:
        data = repo.get(country)
        assert data.languages.tts_code.strip() != "", (
            f"{country} has an empty tts_code"
        )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unsupported_country_raises(repo: ContextRepository) -> None:
    with pytest.raises(CountryNotFoundError) as exc_info:
        repo.get("Antarctica")
    assert "Antarctica" in str(exc_info.value)


def test_error_includes_supported_list(repo: ContextRepository) -> None:
    with pytest.raises(CountryNotFoundError) as exc_info:
        repo.get("Mars")
    # The exception message should hint at supported countries.
    assert exc_info.value.supported  # non-empty list


# ---------------------------------------------------------------------------
# __contains__ helper
# ---------------------------------------------------------------------------


def test_contains_true_for_loaded_country(repo: ContextRepository) -> None:
    assert "Nigeria" in repo
    assert "nigeria" in repo


def test_contains_false_for_unknown(repo: ContextRepository) -> None:
    assert "Antarctica" not in repo


# ---------------------------------------------------------------------------
# Auto-discovery from custom data directory
# ---------------------------------------------------------------------------


def test_custom_data_dir_auto_discovery(tmp_data_dir: Path) -> None:
    custom_repo = ContextRepository(data_dir=tmp_data_dir)
    assert len(custom_repo) == 1
    data = custom_repo.get("Testland")
    assert data.country == "Testland"


def test_schema_json_is_excluded_from_discovery(tmp_data_dir: Path) -> None:
    """schema.json must never be parsed as a country pack."""
    (tmp_data_dir / "schema.json").write_text('{"$schema": "..."}', encoding="utf-8")
    custom_repo = ContextRepository(data_dir=tmp_data_dir)
    assert len(custom_repo) == 1  # only testland.json


# ---------------------------------------------------------------------------
# DataLoadError on bad JSON
# ---------------------------------------------------------------------------


def test_malformed_json_raises_data_load_error(tmp_data_dir: Path) -> None:
    (tmp_data_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DataLoadError):
        ContextRepository(data_dir=tmp_data_dir)


def test_wrong_schema_raises_data_load_error(tmp_data_dir: Path) -> None:
    (tmp_data_dir / "wrong.json").write_text(
        '{"country": 123}', encoding="utf-8"
    )
    with pytest.raises(DataLoadError):
        ContextRepository(data_dir=tmp_data_dir)
