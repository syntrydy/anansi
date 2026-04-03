"""Unit tests for the in-memory job store."""

import asyncio

import pytest

from anansi.api.store import JobStore


@pytest.fixture()
def store() -> JobStore:
    return JobStore()


class TestJobStore:
    def test_create_returns_record(self, store: JobStore) -> None:
        rec = store.create("job-1")
        assert rec.job_id == "job-1"
        assert rec.status == "running"
        assert rec.result is None

    def test_get_existing(self, store: JobStore) -> None:
        store.create("job-2")
        rec = store.get("job-2")
        assert rec is not None
        assert rec.job_id == "job-2"

    def test_get_nonexistent_returns_none(self, store: JobStore) -> None:
        assert store.get("does-not-exist") is None

    def test_delete_removes_job(self, store: JobStore) -> None:
        store.create("job-3")
        store.delete("job-3")
        assert store.get("job-3") is None

    def test_delete_nonexistent_is_safe(self, store: JobStore) -> None:
        store.delete("no-such-job")  # should not raise

    async def test_snapshot_queue_put_and_get(self, store: JobStore) -> None:
        rec = store.create("job-q")
        mock_snap = {"topic": "test"}
        rec.snapshot_queue.put_nowait(mock_snap)  # type: ignore[arg-type]
        item = await rec.snapshot_queue.get()
        assert item == mock_snap

    async def test_sentinel_none_in_queue(self, store: JobStore) -> None:
        rec = store.create("job-s")
        rec.snapshot_queue.put_nowait(None)
        item = await rec.snapshot_queue.get()
        assert item is None
