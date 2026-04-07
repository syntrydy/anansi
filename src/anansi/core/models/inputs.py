from typing import Any, Dict

from pydantic import BaseModel, field_validator

from anansi.core.constants import SUPPORTED_COUNTRIES

class TeacherInput(BaseModel):
    topic: str
    country: str
    grade: str
    language: str
    extra_context: Dict[str, Any] = {}

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if v not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Unsupported country: {v}")
        return v