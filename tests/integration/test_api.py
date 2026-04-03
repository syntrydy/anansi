"""Integration tests for the FastAPI /api/v1 endpoints.

All tests mock run_pipeline to avoid real LLM/API calls.
The ANANSI_MOCK_PIPELINE env var is NOT used here; we mock directly so tests
are deterministic and fast regardless of env configuration.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from anansi.api.main import app
from anansi.api.store import job_store
from anansi.core.models.state import AnansiState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_BODY: dict[str, Any] = {
    "topic": "Water cycle",
    "country": "Kenya",
    "grade": 5,
    "language": "English",
    "audience": "general",
    "aspect_ratio": "1:1",
}

_MOCK_PACKAGE: dict[str, Any] = {
    "panels": [
        {
            "panel_number": 1,
            "panel_id": "p1",
            "title": "Panel 1",
            "caption": "Caption",
            "dialogue": "Dialogue",
            "narration": "Narration",
            "image_url": "",
            "audio_url": "",
            "audio_error": None,
            "safe": True,
            "safety_reason": None,
        }
    ],
    "teacher_guide": "Guide text",
    "safety_results": [],
    "lesson_title": "Water cycle",
}


def _mock_final_state(initial: AnansiState) -> AnansiState:
    return {**initial, "package": _MOCK_PACKAGE}  # type: ignore[typeddict-item]


async def _fake_run_pipeline(
    initial: AnansiState,
    *,
    on_state_update: Any = None,
) -> AnansiState:
    """Instant mock pipeline that emits one snapshot then returns."""
    snap: AnansiState = {**initial, "scenes": [{"title": "Mock scene"}]}  # type: ignore[typeddict-item]
    if on_state_update:
        on_state_update(snap)
    await asyncio.sleep(0)  # yield control
    final = _mock_final_state(initial)
    if on_state_update:
        on_state_update(final)
    return final


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
async def client() -> AsyncClient:  # type: ignore[misc]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_jobs() -> None:  # type: ignore[misc]
    """Ensure test isolation: remove all jobs between tests."""
    job_store._jobs.clear()
    yield
    job_store._jobs.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/lessons
# ---------------------------------------------------------------------------

class TestCreateLesson:
    async def test_returns_job_id(self, client: AsyncClient) -> None:
        with patch("anansi.api.router.run_pipeline", new=AsyncMock(side_effect=_fake_run_pipeline)):
            resp = await client.post("/api/v1/lessons", json=_VALID_BODY)
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    async def test_invalid_country_returns_422(self, client: AsyncClient) -> None:
        body = {**_VALID_BODY, "country": "Antarctica"}
        resp = await client.post("/api/v1/lessons", json=body)
        assert resp.status_code == 422

    async def test_invalid_grade_returns_422(self, client: AsyncClient) -> None:
        body = {**_VALID_BODY, "grade": 0}
        resp = await client.post("/api/v1/lessons", json=body)
        assert resp.status_code == 422

    async def test_missing_topic_returns_422(self, client: AsyncClient) -> None:
        body = {k: v for k, v in _VALID_BODY.items() if k != "topic"}
        resp = await client.post("/api/v1/lessons", json=body)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/lessons/{job_id}
# ---------------------------------------------------------------------------

class TestGetLesson:
    async def test_nonexistent_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/lessons/no-such-id")
        assert resp.status_code == 404

    async def test_running_job_returns_running(self, client: AsyncClient) -> None:
        with patch("anansi.api.router.run_pipeline", new=AsyncMock(side_effect=_fake_run_pipeline)):
            create_resp = await client.post("/api/v1/lessons", json=_VALID_BODY)
        job_id = create_resp.json()["job_id"]
        # Status may be running or done depending on timing; both are valid
        resp = await client.get(f"/api/v1/lessons/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("running", "done")

    async def test_completed_job_has_result(self, client: AsyncClient) -> None:
        with patch("anansi.api.router.run_pipeline", new=AsyncMock(side_effect=_fake_run_pipeline)):
            create_resp = await client.post("/api/v1/lessons", json=_VALID_BODY)
        job_id = create_resp.json()["job_id"]
        # Wait for background task to complete
        await asyncio.sleep(0.2)
        resp = await client.get(f"/api/v1/lessons/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["result"] is not None


# ---------------------------------------------------------------------------
# POST /api/v1/lessons/{job_id}/feedback
# ---------------------------------------------------------------------------

class TestFeedback:
    async def _create_job(self, client: AsyncClient) -> str:
        with patch("anansi.api.router.run_pipeline", new=AsyncMock(side_effect=_fake_run_pipeline)):
            resp = await client.post("/api/v1/lessons", json=_VALID_BODY)
        return resp.json()["job_id"]

    async def test_positive_feedback_accepted(self, client: AsyncClient) -> None:
        job_id = await self._create_job(client)
        resp = await client.post(
            f"/api/v1/lessons/{job_id}/feedback",
            json={"rating": "positive", "comment": "great"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_negative_feedback_accepted(self, client: AsyncClient) -> None:
        job_id = await self._create_job(client)
        resp = await client.post(
            f"/api/v1/lessons/{job_id}/feedback",
            json={"rating": "negative"},
        )
        assert resp.status_code == 200

    async def test_invalid_rating_returns_422(self, client: AsyncClient) -> None:
        job_id = await self._create_job(client)
        resp = await client.post(
            f"/api/v1/lessons/{job_id}/feedback",
            json={"rating": "neutral"},
        )
        assert resp.status_code == 422

    async def test_nonexistent_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/lessons/ghost/feedback",
            json={"rating": "positive"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/lessons/{job_id}/pdf
# ---------------------------------------------------------------------------

class TestPdfEndpoint:
    async def test_pdf_when_job_not_done_returns_409(self, client: AsyncClient) -> None:
        # Manually create a running job without completing it
        from anansi.api.store import job_store
        rec = job_store.create("test-running")
        rec.status = "running"
        resp = await client.get("/api/v1/lessons/test-running/pdf")
        assert resp.status_code == 409

    async def test_pdf_nonexistent_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/lessons/ghost/pdf")
        assert resp.status_code == 404

    async def test_pdf_returns_pdf_bytes(self, client: AsyncClient) -> None:
        from anansi.api.store import job_store
        rec = job_store.create("test-done")
        rec.status = "done"
        rec.result = _MOCK_PACKAGE
        resp = await client.get("/api/v1/lessons/test-done/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# GET /api/v1/meta/countries
# ---------------------------------------------------------------------------

class TestMeta:
    async def test_returns_all_countries(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/meta/countries")
        assert resp.status_code == 200
        data = resp.json()
        assert "countries" in data
        assert set(data["countries"]) == {"Kenya", "Nigeria", "Senegal", "Ghana", "Cameroon"}

    async def test_returns_audiences(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/meta/countries")
        data = resp.json()
        assert set(data["audiences"]) == {"kid", "adult", "general"}

    async def test_returns_aspect_ratios(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/meta/countries")
        data = resp.json()
        assert "1:1" in data["aspect_ratios"]


# ---------------------------------------------------------------------------
# SSE stream (basic smoke test)
# ---------------------------------------------------------------------------

class TestStreamEndpoint:
    async def test_nonexistent_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/lessons/ghost/stream")
        assert resp.status_code == 404

    async def test_already_done_job_emits_done_event(self, client: AsyncClient) -> None:
        from anansi.api.store import job_store
        rec = job_store.create("test-stream-done")
        rec.status = "done"
        rec.result = _MOCK_PACKAGE

        # Collect SSE text; the EventSourceResponse may not fully close in test,
        # so we read with a short timeout.
        chunks: list[str] = []
        try:
            async with client.stream("GET", "/api/v1/lessons/test-stream-done/stream") as r:
                assert r.status_code == 200
                async for line in r.aiter_lines():
                    chunks.append(line)
                    if "done" in line:
                        break
        except Exception:
            pass

        combined = "\n".join(chunks)
        assert "done" in combined
