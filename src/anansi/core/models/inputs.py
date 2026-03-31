from typing import Any, Dict

from pydantic import BaseModel, validator

from anansi.core.constants import SUPPORTED_COUNTRIES

class TeacherInput(BaseModel):
    topic: str
    country: str
    grade: int
    language: str
    extra_context: Dict[str, Any] = {}

    @validator("country")
    def validate_country(cls, v: str) -> str:
        if v not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Unsupported country: {v}")
        return v