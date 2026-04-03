"""SSE generator: bridges AnansiState snapshots from the job queue to HTTP."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from sse_starlette.sse import ServerSentEvent

from anansi.api.store import JobRecord, JobStore

logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 30  # seconds between keepalive comments
_QUEUE_TIMEOUT = 120       # seconds to wait for next snapshot before giving up


async def sse_generator(
    job_id: str,
    store: JobStore,
) -> AsyncGenerator[ServerSentEvent, None]:
    """
    Yield SSE events for a running pipeline job.

    Events:
      snapshot  — JSON-encoded AnansiState dict after each pipeline node
      done      — pipeline finished (or job already done when client connects)
      error     — pipeline raised an exception
      keepalive — comment sent every 30s to prevent proxy timeouts
    """
    record = store.get(job_id)
    if record is None:
        return

    # If the job already finished before the client connected, emit the final
    # state immediately rather than blocking on the queue.
    if record.status == "done":
        if record.result is not None:
            yield ServerSentEvent(
                data=json.dumps({"type": "snapshot", **record.result}),
                event="snapshot",
            )
        yield ServerSentEvent(data=json.dumps({"type": "done", "job_id": job_id}), event="done")
        return
    if record.status == "error":
        yield ServerSentEvent(
            data=json.dumps({"type": "error", "message": record.error or "Unknown error"}),
            event="error",
        )
        return

    keepalive_task: asyncio.Task[Any] | None = None

    async def _keepalive(queue: asyncio.Queue[Any]) -> None:
        while True:
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
            await queue.put("__keepalive__")

    # Start keepalive pump — pushes a sentinel into the queue so the main loop
    # wakes up and can yield a comment without relying on asyncio.wait_for alone.
    keepalive_task = asyncio.create_task(_keepalive(record.snapshot_queue))

    try:
        while True:
            try:
                item = await asyncio.wait_for(
                    record.snapshot_queue.get(), timeout=_QUEUE_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning("SSE timeout waiting for job %s", job_id)
                yield ServerSentEvent(
                    data=json.dumps({"type": "error", "message": "Pipeline timed out"}),
                    event="error",
                )
                return

            if item == "__keepalive__":
                yield ServerSentEvent(data=": keepalive", event="keepalive")
                continue

            if item is None:  # sentinel → pipeline finished
                if record.status == "error":
                    yield ServerSentEvent(
                        data=json.dumps({"type": "error", "message": record.error or "Unknown error"}),
                        event="error",
                    )
                else:
                    yield ServerSentEvent(
                        data=json.dumps({"type": "done", "job_id": job_id}),
                        event="done",
                    )
                return

            # Normal snapshot
            try:
                payload = json.dumps({"type": "snapshot", **dict(item)})
            except (TypeError, ValueError) as exc:
                logger.warning("Could not serialise snapshot for job %s: %s", job_id, exc)
                continue
            yield ServerSentEvent(data=payload, event="snapshot")

    finally:
        if keepalive_task:
            keepalive_task.cancel()
