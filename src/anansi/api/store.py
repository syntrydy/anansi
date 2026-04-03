"""In-memory job store: bridges background pipeline tasks with SSE streams."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from anansi.core.models.state import AnansiState

logger = logging.getLogger(__name__)

_JOB_TTL_SECONDS = 3600  # 1 hour


@dataclass
class JobRecord:
    job_id: str
    status: Literal["running", "done", "error"] = "running"
    result: dict[str, Any] | None = None
    error: str | None = None
    # None sentinel signals end-of-stream to the SSE generator
    snapshot_queue: asyncio.Queue[AnansiState | None] = field(
        default_factory=lambda: asyncio.Queue()
    )
    task: asyncio.Task[None] | None = None
    created_at: float = field(default_factory=time.monotonic)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create(self, job_id: str) -> JobRecord:
        record = JobRecord(job_id=job_id)
        self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def cleanup_loop(self) -> None:
        """Periodically remove jobs older than TTL."""
        while True:
            await asyncio.sleep(300)  # check every 5 minutes
            now = time.monotonic()
            stale = [
                jid
                for jid, rec in self._jobs.items()
                if now - rec.created_at > _JOB_TTL_SECONDS
            ]
            for jid in stale:
                rec = self._jobs.pop(jid, None)
                if rec and rec.task and not rec.task.done():
                    rec.task.cancel()
            if stale:
                logger.info("JobStore: evicted %d stale job(s)", len(stale))


# Singleton instance shared across the FastAPI app via dependency injection.
job_store = JobStore()
