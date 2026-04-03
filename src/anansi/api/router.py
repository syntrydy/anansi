"""FastAPI router: all /api/v1 endpoints."""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from anansi.agent.graph import run_pipeline
from anansi.api.schemas import (
    FeedbackRequest,
    JobCreatedResponse,
    JobStatusResponse,
    LessonRequest,
    MetaResponse,
)
from anansi.api.store import job_store
from anansi.api.streaming import sse_generator
from anansi.core.constants import SUPPORTED_COUNTRIES
from anansi.core.models.state import AnansiState, initialize_state
from anansi.observability.feedback import log_feedback
from anansi.ui.components.export_pdf import _build_filename, build_pdf_bytes

logger = logging.getLogger(__name__)

router = APIRouter()

_MOCK_PIPELINE = os.getenv("ANANSI_MOCK_PIPELINE", "0") == "1"


# ── Background pipeline runner ────────────────────────────────────────────────

async def _run_pipeline_job(job_id: str, initial: AnansiState) -> None:
    record = job_store.get(job_id)
    if record is None:
        return
    try:
        if _MOCK_PIPELINE:
            # Emit a single minimal snapshot then a package for local dev/testing
            import asyncio

            mock_snap: AnansiState = {**initial, "scenes": [{"title": "Mock scene"}]}  # type: ignore[typeddict-item]
            record.snapshot_queue.put_nowait(mock_snap)
            await asyncio.sleep(0.05)
            mock_final: AnansiState = {
                **mock_snap,
                "package": {
                    "panels": [
                        {
                            "panel_number": 1,
                            "panel_id": "mock-1",
                            "title": "Mock Panel",
                            "caption": "Mock caption",
                            "dialogue": "Mock dialogue",
                            "narration": "Mock narration",
                            "image_url": "",
                            "audio_url": "",
                            "audio_error": None,
                            "safe": True,
                            "safety_reason": None,
                        }
                    ],
                    "teacher_guide": "Mock teacher guide.",
                    "safety_results": [],
                    "lesson_title": initial.get("topic", "Mock Lesson"),
                },
            }  # type: ignore[typeddict-item]
            record.snapshot_queue.put_nowait(mock_final)
            record.result = mock_final["package"]
            record.status = "done"
        else:
            def on_update(snap: AnansiState) -> None:
                record.snapshot_queue.put_nowait(snap)

            final = await run_pipeline(initial, on_state_update=on_update)
            record.result = final.get("package")
            record.status = "done"
    except Exception as exc:
        logger.exception("Pipeline failed for job %s", job_id)
        record.status = "error"
        record.error = str(exc)
    finally:
        # Sentinel: close the SSE stream
        record.snapshot_queue.put_nowait(None)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/lessons", response_model=JobCreatedResponse, status_code=202)
async def create_lesson(
    body: LessonRequest,
    background_tasks: BackgroundTasks,
) -> JobCreatedResponse:
    """Submit a lesson request; returns a job_id to stream progress via SSE."""
    job_id = str(uuid4())
    record = job_store.create(job_id)
    initial = initialize_state(body.model_dump())
    background_tasks.add_task(_run_pipeline_job, job_id, initial)
    return JobCreatedResponse(job_id=job_id)


@router.get("/lessons/{job_id}/stream")
async def stream_lesson(job_id: str) -> EventSourceResponse:
    """SSE stream: emits snapshot events during pipeline execution, then done/error."""
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return EventSourceResponse(sse_generator(job_id, job_store))


@router.get("/lessons/{job_id}", response_model=JobStatusResponse)
async def get_lesson(job_id: str) -> JobStatusResponse:
    """Poll endpoint: returns current job status and result when done."""
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobStatusResponse(
        job_id=job_id,
        status=record.status,
        result=record.result,
        error=record.error,
    )


@router.post("/lessons/{job_id}/feedback", status_code=200)
async def submit_feedback(job_id: str, body: FeedbackRequest) -> dict[str, Any]:
    """Log teacher feedback for a completed lesson."""
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    log_feedback(
        rating=body.rating,
        comment=body.comment,
        result=record.result or {},
        last_input={},
    )
    return {"status": "ok"}


@router.get("/lessons/{job_id}/pdf")
async def download_pdf(
    job_id: str,
    exclude_unsafe: bool = True,
    topic: str = "",
    country: str = "",
    grade: str = "",
) -> Response:
    """Build and return the lesson PDF as a binary download."""
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if record.status != "done" or record.result is None:
        raise HTTPException(status_code=409, detail="Lesson not ready yet")

    pdf_bytes = build_pdf_bytes(record.result, exclude_unsafe=exclude_unsafe)
    filename = _build_filename(topic, country, grade)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/meta/countries", response_model=MetaResponse)
async def get_meta() -> MetaResponse:
    """Return enumerable values for form dropdowns."""
    return MetaResponse(
        countries=sorted(SUPPORTED_COUNTRIES),
        languages=["English", "Swahili", "French"],
        audiences=["kid", "adult", "general"],
        aspect_ratios=["1:1", "16:9", "4:3"],
    )
