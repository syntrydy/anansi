"""LangGraph state shape: plain dict at runtime, TypedDict for typing."""

from typing import Any, NotRequired, TypedDict

from anansi.core.models.inputs import TeacherInput


class AnansiState(TypedDict):
    """State merged across nodes; extra keys appear as the pipeline runs."""

    topic: str
    country: str
    grade: str
    language: str
    audience: str        # derived internally from grade age; not in API request
    aspect_ratio: str    # always "1:1"; hardcoded, not exposed in API
    extra_context: dict[str, Any]
    scenes: NotRequired[list[dict[str, Any]]]
    context_pack: NotRequired[dict[str, Any]]
    panel_scripts: NotRequired[list[dict[str, Any]]]
    images: NotRequired[list[dict[str, Any]]]
    audios: NotRequired[list[dict[str, Any]]]
    safety_results: NotRequired[list[dict[str, Any]]]
    package: NotRequired[dict[str, Any]]


def _derive_audience(country: str, grade_label: str) -> str:
    """Look up the grade's age from the country pack and derive audience tier."""
    import json
    from pathlib import Path
    data_dir = Path(__file__).parent.parent.parent / "context" / "data"
    pack_path = data_dir / f"{country.lower()}.json"
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for level in pack.get("grade_levels", []):
            if level["label"] == grade_label:
                age = level["age"]
                return "kid" if age < 14 else "general"
    except Exception:
        pass
    return "kid"  # safe default for classroom use


def initialize_state(input_data: dict[str, Any]) -> AnansiState:
    """Validate teacher input and return initial graph state (a plain dict)."""
    validated = TeacherInput(**input_data)
    audience = _derive_audience(validated.country, validated.grade)
    return {
        "topic": validated.topic,
        "country": validated.country,
        "grade": validated.grade,
        "language": validated.language,
        "audience": audience,
        "aspect_ratio": "1:1",
        "extra_context": validated.extra_context,
    }
