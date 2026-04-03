"""LangGraph state shape: plain dict at runtime, TypedDict for typing."""

from typing import Any, NotRequired, TypedDict

from anansi.core.models.inputs import TeacherInput


class AnansiState(TypedDict):
    """State merged across nodes; extra keys appear as the pipeline runs."""

    topic: str
    country: str
    grade: int
    language: str
    audience: str
    aspect_ratio: str
    extra_context: dict[str, Any]
    scenes: NotRequired[list[dict[str, Any]]]
    context_pack: NotRequired[dict[str, Any]]
    panel_scripts: NotRequired[list[dict[str, Any]]]
    images: NotRequired[list[dict[str, Any]]]
    audios: NotRequired[list[dict[str, Any]]]
    safety_results: NotRequired[list[dict[str, Any]]]
    package: NotRequired[dict[str, Any]]


def initialize_state(input_data: dict[str, Any]) -> AnansiState:
    """Validate teacher input and return initial graph state (a plain dict)."""
    validated = TeacherInput(**input_data)
    return {
        "topic": validated.topic,
        "country": validated.country,
        "grade": validated.grade,
        "language": validated.language,
        "audience": validated.audience,
        "aspect_ratio": validated.aspect_ratio,
        "extra_context": validated.extra_context,
    }
