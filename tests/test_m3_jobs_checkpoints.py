"""M3 persistence slice: durable job queue and checkpoint store."""

from __future__ import annotations

import time
from pathlib import Path

from conflux.adapters.sqlite_store import (
    CheckpointStore,
    JobQueue,
    SCHEMA_MIGRATIONS,
    SQLiteDatabase,
)
from conflux.core.runtime_home import database_path


def _queue(tmp_path: Path, *, lease_seconds: float = 60.0) -> JobQueue:
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    db.bootstrap_schema()
    return JobQueue(db, lease_seconds=lease_seconds)


def test_schema_version_includes_jobs_and_checkpoints(tmp_path: Path) -> None:
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    db.bootstrap_schema()
    assert db.schema_version() == len(SCHEMA_MIGRATIONS)
    db.close()


def test_enqueue_is_idempotent_by_key(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    first = queue.enqueue("paper_radar", {"project": "p1"}, idempotency_key="radar-p1-v1")
    second = queue.enqueue("paper_radar", {"project": "p1"}, idempotency_key="radar-p1-v1")
    assert first["job_id"] == second["job_id"]
    assert queue.stats() == {"pending": 1}


def test_claim_is_exclusive(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queue.enqueue("research", {"query": "q"}, idempotency_key="q1")
    claimed = queue.claim("worker-a")
    assert claimed is not None
    assert claimed["status"] == "running"
    assert claimed["lease_owner"] == "worker-a"
    assert claimed["attempts"] == 1
    assert queue.claim("worker-b") is None


def test_claim_can_filter_by_job_kind(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queue.enqueue("research", {"query": "q"}, idempotency_key="research-q")
    radar = queue.enqueue("paper_radar", {"project": "p1"}, idempotency_key="radar-p1")

    claimed = queue.claim("worker-a", kind="paper_radar")

    assert claimed is not None
    assert claimed["job_id"] == radar["job_id"]
    assert claimed["kind"] == "paper_radar"


def test_expired_lease_can_be_reclaimed(tmp_path: Path) -> None:
    queue = _queue(tmp_path, lease_seconds=0.01)
    queue.enqueue("research", {"query": "q"}, idempotency_key="q1")
    first = queue.claim("worker-a")
    assert first is not None
    time.sleep(0.02)
    second = queue.claim("worker-b")
    assert second is not None
    assert second["lease_owner"] == "worker-b"
    assert second["attempts"] == 2


def test_expired_lease_at_attempt_limit_becomes_failed(tmp_path: Path) -> None:
    queue = _queue(tmp_path, lease_seconds=0.01)
    job = queue.enqueue("research", {"query": "q"}, idempotency_key="q-limit", max_attempts=1)
    assert queue.claim("worker-a") is not None
    time.sleep(0.02)

    expired = queue.expire_exhausted()

    assert [item["job_id"] for item in expired] == [job["job_id"]]
    assert queue.claim("worker-b") is None
    assert queue.get(job["job_id"])["status"] == "failed"


def test_heartbeat_renews_lease_and_checks_owner(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queue.enqueue("research", {}, idempotency_key="q1")
    job = queue.claim("worker-a")
    assert job is not None
    old_expiry = job["lease_expires_at"]
    assert queue.heartbeat(job["job_id"], "worker-a") is True
    renewed = queue.get(job["job_id"])
    assert renewed["lease_expires_at"] > old_expiry
    assert queue.heartbeat(job["job_id"], "worker-b") is False


def test_complete_terminates_job(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    job = queue.enqueue("research", {"query": "q"}, idempotency_key="q1")
    claimed = queue.claim("worker-a")
    assert claimed is not None
    assert queue.complete(job["job_id"], "worker-a") is True
    assert queue.get(job["job_id"])["status"] == "completed"
    assert queue.claim("worker-b") is None


def test_fail_retries_then_fails_permanently(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    job = queue.enqueue("research", {}, idempotency_key="q1", max_attempts=2)
    queue.claim("worker-a")
    assert queue.fail(job["job_id"], "worker-a", "boom", retry_delay=0) is True
    retry = queue.get(job["job_id"])
    assert retry["status"] == "pending"
    assert retry["attempts"] == 1

    queue.claim("worker-b")
    assert queue.fail(job["job_id"], "worker-b", "boom again", retry_delay=0) is True
    assert queue.get(job["job_id"])["status"] == "failed"


def test_cancel_active_jobs(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    pending = queue.enqueue("research", {}, idempotency_key="pending")
    running = queue.enqueue("research", {}, idempotency_key="running")
    queue.claim("worker-a")
    assert queue.cancel(pending["job_id"]) is True
    assert queue.cancel(running["job_id"]) is True
    assert queue.cancel(pending["job_id"]) is False
    assert queue.get(running["job_id"])["status"] == "cancelled"


def test_checkpoint_save_load_latest_list_delete_across_connections(tmp_path: Path) -> None:
    db_path = database_path(tmp_path)
    SQLiteDatabase(db_path).connect().bootstrap_schema()
    store = CheckpointStore(SQLiteDatabase(db_path).connect())
    store.save("thread-1", "step-1", {"done": True})
    store.save("thread-1", "step-2", {"done": False})
    store.save("thread-1", "step-1", {"done": True, "revised": 1})

    reopened = CheckpointStore(SQLiteDatabase(db_path).connect())
    assert reopened.load("thread-1", "step-1") == {"done": True, "revised": 1}
    # step-1 was updated last, so it is the latest checkpoint for the thread.
    assert reopened.load("thread-1") == {"done": True, "revised": 1}
    assert [item["step_id"] for item in reopened.list("thread-1")] == ["step-1", "step-2"]
    assert reopened.delete("thread-1", "step-1") == 1
    assert reopened.load("thread-1", "step-1") is None
    assert reopened.delete("thread-1") == 1
    assert reopened.list("thread-1") == []
