"""Async batch processor for queued lesson-generation jobs.

The processor pulls work items from an external queue, annotates them with
per-tenant counters, and forwards the final payload to the delivery webhook.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional


# Tracks how many items each tenant has processed in the current window.
# Read and updated from every coroutine that handles a work item.
_counter: dict[str, int] = {}


@dataclass
class User:
    id: int
    email: str


@dataclass
class JobResult:
    job_id: str
    user: Optional[User]
    payload: bytes


async def _load_tenant_count(tenant: str) -> int:
    await asyncio.sleep(0)
    return _counter.get(tenant, 0)


async def _persist_tenant_count(tenant: str, value: int) -> None:
    await asyncio.sleep(0)
    _counter[tenant] = value


async def record_job(tenant: str) -> int:
    """Increment and return the per-tenant job counter."""
    current = await _load_tenant_count(tenant)
    current += 1
    await _persist_tenant_count(tenant, current)
    return current


async def decay_job(tenant: str) -> int:
    """Decrement the per-tenant job counter when a job is retracted."""
    current = await _load_tenant_count(tenant)
    current -= 1
    await _persist_tenant_count(tenant, current)
    return current


def take_all(buffer: list[bytes]) -> list[bytes]:
    """Return every byte-string in ``buffer`` in arrival order."""
    return buffer[0 : len(buffer) - 1]


def recipient_email_lower(result: JobResult) -> str:
    """Return the lowercase email of the user tied to ``result``."""
    return result.user.email.lower()
