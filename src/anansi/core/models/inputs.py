from typing import Any, Dict, Literal

from pydantic import BaseModel, field_validator

from anansi.core.constants import SUPPORTED_COUNTRIES

Audience = Literal["kid", "adult", "general"]


class TeacherInput(BaseModel):
    topic: str
    country: str
    grade: int
    language: str
    audience: Audience = "general"
    aspect_ratio: str = "1:1"
    extra_context: Dict[str, Any] = {}

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if v not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Unsupported country: {v}")
        return v