from typing import TypedDict, Dict, Any
from anansi.core.models.inputs import TeacherInput

class AnansiState(TypedDict):
    topic: str
    country: str
    grade: int
    language: str
    extra_context: Dict[str, Any]

def initialize_state(input_data: dict) -> AnansiState:
    validated = TeacherInput(**input_data)
    return AnansiState(
        topic=validated.topic,
        country=validated.country,
        grade=validated.grade,
        language=validated.language,
        extra_context=validated.extra_context,
    )