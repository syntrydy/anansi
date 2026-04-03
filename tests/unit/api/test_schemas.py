"""Unit tests for API request/response schemas."""

import pytest
from pydantic import ValidationError

from anansi.api.schemas import FeedbackRequest, LessonRequest


class TestLessonRequest:
    def test_valid_request(self) -> None:
        req = LessonRequest(
            topic="Water cycle",
            country="Kenya",
            grade=5,
            language="English",
        )
        assert req.topic == "Water cycle"
        assert req.audience == "general"
        assert req.aspect_ratio == "1:1"

    def test_invalid_country_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unsupported country"):
            LessonRequest(topic="t", country="Antarctica", grade=3, language="English")

    def test_grade_below_range_raises(self) -> None:
        with pytest.raises(ValidationError, match="grade must be between"):
            LessonRequest(topic="t", country="Kenya", grade=0, language="English")

    def test_grade_above_range_raises(self) -> None:
        with pytest.raises(ValidationError, match="grade must be between"):
            LessonRequest(topic="t", country="Kenya", grade=13, language="English")

    def test_all_supported_countries_accepted(self) -> None:
        for country in ("Kenya", "Nigeria", "Senegal", "Ghana", "Cameroon"):
            req = LessonRequest(topic="t", country=country, grade=5, language="English")
            assert req.country == country

    def test_audience_defaults_to_general(self) -> None:
        req = LessonRequest(topic="t", country="Ghana", grade=4, language="English")
        assert req.audience == "general"

    def test_extra_context_defaults_empty(self) -> None:
        req = LessonRequest(topic="t", country="Ghana", grade=4, language="English")
        assert req.extra_context == {}


class TestFeedbackRequest:
    def test_positive_rating(self) -> None:
        fb = FeedbackRequest(rating="positive")
        assert fb.rating == "positive"
        assert fb.comment == ""

    def test_negative_rating_with_comment(self) -> None:
        fb = FeedbackRequest(rating="negative", comment="needs more images")
        assert fb.rating == "negative"
        assert fb.comment == "needs more images"

    def test_invalid_rating_raises(self) -> None:
        with pytest.raises(ValidationError):
            FeedbackRequest(rating="neutral")  # type: ignore[arg-type]
