"""HTTP request/response schemas for the Anansi REST API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, field_validator

from anansi.core.constants import SUPPORTED_COUNTRIES


class LessonRequest(BaseModel):
    topic: str
    country: str
    grade: str
    language: str
    extra_context: dict[str, Any] = {}

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if v not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Unsupported country '{v}'. Choose from: {sorted(SUPPORTED_COUNTRIES)}")
        return v


class FeedbackRequest(BaseModel):
    rating: Literal["positive", "negative"]
    comment: str = ""


class JobCreatedResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["running", "done", "error"]
    result: dict[str, Any] | None = None
    error: str | None = None


class GradeLevel(BaseModel):
    label: str
    age: int


class MetaResponse(BaseModel):
    countries: list[str]
    languages: list[str]
    grade_levels: dict[str, list[GradeLevel]]
