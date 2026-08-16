"""M3 durable Workbench research-query jobs and run-local configuration."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from conflux import config
from conflux.adapters.sqlite_store import (
    CheckpointStore,
    EventStore,
    JobQueue,
    RunStore,
    SQLiteDatabase,
)
from conflux.trace import TraceEvent
from conflux.workbench.jobs import JobManager, RESEARCH_JOB_KIND


def _wait_for_status(manager: JobManager, run_id: str, statuses: set[str]) -> dict:
    deadline = time.time() + 5.0
    while time.time() < deadline:
        status = manager.get(run_id)
        if status and status["status"] in statuses:
            return status
        time.sleep(0.02)
    raise AssertionError(f"job {run_id} did not reach {sorted(statuses)}")


def _fake_query_command(query: str, **kwargs):
    state = {
        "query": query,
        "_pipeline_stage": "completed",
        "_run_status": "completed",
        "_delivery_status": "diagnostic_only",
        "_run_summary": {"mode": "answer_first"},
        "_source_statuses": {},
        "_audit_metrics": {},
    }
    event = TraceEvent(
        stage="research_plan",
        status="completed",
        elapsed_ms=1.0,
        summary="planned",
        run_id=kwargs["run_id"],
        thread_id=kwargs["run_id"],
    )
    kwargs["should_stop"]()
    kwargs["on_graph_state"](state, [event])
    kwargs["should_stop"]()
    return state


def test_query_job_persists_without_secrets_and_is_visible_to_new_manager(tmp_path: Path) -> None:
    db_path = tmp_path / "conflux.db"
    first = JobManager(db_path=db_path, start_worker=False)
    submitted = first.submit(
        "durable query",
        {
            "depth": "quick",
            "model": "test-model",
            "api_key": "reasoning-secret",
            "embedding_api_key": "embedding-secret",
        },
    )

    db = SQLiteDatabase(db_path).connect()
    try:
        queued = JobQueue(db).get(submitted["run_id"])
        assert queued is not None
        serialized = json.dumps(queued["payload"], ensure_ascii=False)
        assert "reasoning-secret" not in serialized
        assert "embedding-secret" not in serialized
        assert "api_key" not in serialized
        assert queued["kind"] == RESEARCH_JOB_KIND
    finally:
        db.close()

    reopened = JobManager(db_path=db_path, start_worker=False)
    status = reopened.get(submitted["run_id"])
    assert status is not None
    assert status["query"] == "durable query"
    assert status["status"] == "pending"
    assert reopened.list()[0]["run_id"] == submitted["run_id"]


def test_query_worker_recovers_pending_job_and_persists_events_and_checkpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    monkeypatch.setattr(cli, "query_command", _fake_query_command)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("resume me", {"depth": "quick"})["run_id"]

    worker = JobManager(db_path=db_path, poll_interval=0.02)
    status = _wait_for_status(worker, run_id, {"completed_diagnostic"})
    worker.close()

    assert status["pipeline"] == "answer_first"
    db = SQLiteDatabase(db_path).connect()
    try:
        assert EventStore(db).list(run_id=run_id)
        checkpoint = CheckpointStore(db).load(run_id)
        assert checkpoint is not None
        assert checkpoint["complete"] is True
        assert checkpoint["terminal_result"]["public_status"] == "completed_diagnostic"
        assert RunStore(db).last_step(run_id)["output"]["stage"] == "completed"
    finally:
        db.close()


def test_query_failure_persists_structured_diagnostic_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    def broken_query(*_args, **_kwargs):
        raise TypeError("cannot unpack non-iterable BudgetedChatModel object")

    monkeypatch.setattr(cli, "query_command", broken_query)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "panel contract smoke",
        {"depth": "standard", "output_dir": str(output_dir)},
    )["run_id"]
    status = _wait_for_status(manager, run_id, {"failed"})
    manager.close()

    assert status["has_report"] is False
    assert "cannot unpack" in status["error"]
    diagnostic_json = Path(status["artifacts"]["diagnostic_json_path"])
    diagnostic_markdown = Path(status["artifacts"]["diagnostic_markdown_path"])
    assert diagnostic_json.is_file()
    assert diagnostic_markdown.is_file()
    diagnostic = json.loads(diagnostic_json.read_text(encoding="utf-8"))
    assert diagnostic["schema_version"] == "conflux.research_failure.v1"
    assert diagnostic["status"] == "failed"
    assert diagnostic["error_type"] == "TypeError"
    assert diagnostic["recovery"]["retryable"] is False
    assert "panel contract smoke" in diagnostic_markdown.read_text(encoding="utf-8")


def test_expired_query_lease_is_reclaimed_and_records_resume_event(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    monkeypatch.setattr(cli, "query_command", _fake_query_command)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("recover expired", {"depth": "quick"})["run_id"]
    db = SQLiteDatabase(db_path).connect()
    try:
        claimed = JobQueue(db, lease_seconds=0.01).claim("dead-worker", kind=RESEARCH_JOB_KIND)
        assert claimed is not None
    finally:
        db.close()
    time.sleep(0.03)

    worker = JobManager(db_path=db_path, poll_interval=0.02)
    _wait_for_status(worker, run_id, {"completed_diagnostic"})
    worker.close()

    reopened = JobManager(db_path=db_path, start_worker=False)
    resume_events = [event for event in reopened.events(run_id) if event["stage"] == "job_resume"]
    assert len(resume_events) == 1
    assert resume_events[0]["metadata"]["attempt"] == 2


def test_query_job_recovers_after_worker_process_termination(tmp_path: Path) -> None:
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("process crash recovery", {"depth": "quick"})["run_id"]
    blocking_script = textwrap.dedent(
        """
        import sys
        import time
        from conflux import __main__ as cli
        from conflux.workbench.jobs import JobManager

        def blocking_query(*args, **kwargs):
            time.sleep(30)

        cli.query_command = blocking_query
        JobManager(db_path=sys.argv[1], poll_interval=0.02, lease_seconds=3.0)
        time.sleep(30)
        """
    )
    first_worker = subprocess.Popen(
        [sys.executable, "-c", blocking_script, str(db_path)],
        cwd=Path.cwd(),
    )
    try:
        # P1.1: window is event-driven (poll until running), not a fixed 5s
        # assertion. Cold-start import of conflux in a fresh subprocess measured
        # at claim P95 ~4.8s / max 5.6s, so a hard 5s window races the worker.
        deadline = time.time() + 30.0
        lease_expires_at = 0.0
        while time.time() < deadline:
            db = SQLiteDatabase(db_path).connect()
            try:
                queued = JobQueue(db).get(run_id)
            finally:
                db.close()
            if queued and queued["status"] == "running":
                lease_expires_at = float(queued["lease_expires_at"] or 0.0)
                break
            time.sleep(0.02)
        assert lease_expires_at > 0
    finally:
        first_worker.terminate()
        first_worker.wait(timeout=5)

    time.sleep(max(0.0, lease_expires_at - time.time()) + 0.2)
    recovery_script = textwrap.dedent(
        """
        import sys
        import time
        from conflux import __main__ as cli
        from conflux.trace import TraceEvent
        from conflux.workbench.jobs import JobManager

        def fake_query(query, **kwargs):
            state = {
                '_pipeline_stage': 'completed',
                '_run_status': 'completed',
                '_delivery_status': 'diagnostic_only',
                '_run_summary': {'mode': 'answer_first'},
                '_source_statuses': {},
                '_audit_metrics': {},
            }
            event = TraceEvent(
                stage='research_plan', status='completed', elapsed_ms=1,
                summary='recovered', run_id=kwargs['run_id'], thread_id=kwargs['run_id'],
            )
            kwargs['on_graph_state'](state, [event])
            return state

        cli.query_command = fake_query
        manager = JobManager(db_path=sys.argv[1], poll_interval=0.02, lease_seconds=3.0)
        deadline = time.time() + 30
        while time.time() < deadline:
            status = manager.get(sys.argv[2])
            if status and status['status'] == 'completed_diagnostic':
                manager.close()
                raise SystemExit(0)
            time.sleep(0.02)
        manager.close()
        raise SystemExit(2)
        """
    )
    recovered = subprocess.run(
        [sys.executable, "-c", recovery_script, str(db_path), run_id],
        cwd=Path.cwd(),
        timeout=35,
        check=False,
    )

    assert recovered.returncode == 0
    reopened = JobManager(db_path=db_path, start_worker=False)
    assert reopened.get(run_id)["status"] == "completed_diagnostic"
    assert any(event["stage"] == "job_resume" for event in reopened.events(run_id))


def test_persisted_cancel_is_terminal_and_not_claimed_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("cancel me", {"depth": "quick"})["run_id"]
    assert submitter.cancel(run_id) is True

    restarted = JobManager(db_path=db_path, poll_interval=0.02)
    time.sleep(0.08)
    status = restarted.get(run_id)
    restarted.close()

    assert status is not None
    assert status["status"] == "cancelled"
    assert status["cancel_reason"] == "user"


def test_running_cancel_cannot_be_overwritten_by_query_completion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    entered = threading.Event()
    release = threading.Event()

    def cancellable_query(query: str, **kwargs):
        entered.set()
        assert release.wait(2.0)
        kwargs["should_stop"]()
        return {"_delivery_status": "diagnostic_only", "_run_summary": {"mode": "answer_first"}}

    monkeypatch.setattr(cli, "query_command", cancellable_query)
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit("cancel while running", {"depth": "quick"})["run_id"]
    assert entered.wait(2.0)
    assert manager.cancel(run_id) is True
    release.set()
    status = _wait_for_status(manager, run_id, {"cancelled"})
    manager.close()

    assert status["cancel_reason"] == "user"
    assert status["status"] == "cancelled"


def test_final_checkpoint_completes_reclaimed_job_without_duplicate_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    def unexpected_query(*args, **kwargs):
        raise AssertionError("terminal checkpoint must prevent duplicate query execution")

    monkeypatch.setattr(cli, "query_command", unexpected_query)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("already committed", {"depth": "quick"})["run_id"]
    terminal = {
        "kind": RESEARCH_JOB_KIND,
        "query": "already committed",
        "public_status": "completed",
        "started_at": time.time() - 1,
        "ended_at": time.time(),
        "timeout_seconds": 180,
        "deadline_at": time.time() + 10,
        "commit_reserve_seconds": 15,
        "final_answer": "done",
        "has_report": True,
        "artifacts": {"markdown_path": "report.md"},
        "warnings": [],
    }
    db = SQLiteDatabase(db_path).connect()
    try:
        CheckpointStore(db).save(
            run_id,
            "final",
            {"complete": True, "stage": "completed", "terminal_result": terminal},
        )
    finally:
        db.close()

    restarted = JobManager(db_path=db_path, poll_interval=0.02)
    status = _wait_for_status(restarted, run_id, {"completed"})
    restarted.close()
    assert status["final_answer"] == "done"


def test_event_cursor_survives_manager_recreation(tmp_path: Path) -> None:
    db_path = tmp_path / "conflux.db"
    manager = JobManager(db_path=db_path, start_worker=False)
    run_id = manager.submit("events", {"depth": "quick"})["run_id"]
    db = SQLiteDatabase(db_path).connect()
    try:
        store = EventStore(db)
        first_id = store.append(
            TraceEvent(stage="one", status="completed", elapsed_ms=1, run_id=run_id)
        )
        second_id = store.append(
            TraceEvent(stage="two", status="completed", elapsed_ms=2, run_id=run_id)
        )
    finally:
        db.close()

    reopened = JobManager(db_path=db_path, start_worker=False)
    events = reopened.events(run_id, after_id=first_id)
    assert [event["event_id"] for event in events] == [second_id]


def test_config_overrides_are_context_local_across_threads(monkeypatch) -> None:
    monkeypatch.delenv("CONFLUX_MODELS__QUICK__MODEL", raising=False)
    monkeypatch.setattr(config, "_config", {"models": {"quick": {"model": "base"}}})
    barrier = threading.Barrier(2)
    observed: dict[str, tuple[str, str | None]] = {}

    def read_override(name: str, model: str) -> None:
        with config.override({"CONFLUX_MODELS__QUICK__MODEL": model}):
            barrier.wait()
            observed[name] = (
                str(config.get("models", "quick", "model")),
                config.os.environ.get("CONFLUX_MODELS__QUICK__MODEL"),
            )

    first = threading.Thread(target=read_override, args=("first", "model-a"))
    second = threading.Thread(target=read_override, args=("second", "model-b"))
    first.start()
    second.start()
    first.join()
    second.join()

    assert observed == {
        "first": ("model-a", None),
        "second": ("model-b", None),
    }
    assert config.get("models", "quick", "model") == "base"


def test_config_override_propagates_to_graph_executor_workers(monkeypatch) -> None:
    monkeypatch.setattr(config, "_config", {"retrieval": {"top_k": 10}})
    with config.override({"CONFLUX_RETRIEVAL__TOP_K": "3"}):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = config.submit_with_context(
                executor,
                config.get,
                "retrieval",
                "top_k",
            )
            assert future.result() == 3
    assert config.get("retrieval", "top_k") == 10


def test_query_job_path_has_no_global_execution_patch() -> None:
    source = Path("src/conflux/workbench/jobs.py").read_text(encoding="utf-8")
    assert "_EXECUTION_LOCK" not in source
    assert "_temporary_env" not in source
    assert "_run_phase2_graph =" not in source


# --- P1.2: submit idempotency + queue backpressure ---


def test_submit_idempotency_same_key_returns_same_run_without_duplicate(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    first = manager.submit("idempotent query", {"depth": "quick"}, idempotency_key="key-1")
    second = manager.submit("idempotent query", {"depth": "quick"}, idempotency_key="key-1")

    assert second["run_id"] == first["run_id"]
    assert second["status"] == first["status"]
    assert second.get("idempotent_replay") is True

    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        jobs = JobQueue(db).list(kind=RESEARCH_JOB_KIND)
        assert len(jobs) == 1
        assert jobs[0]["run_id"] == first["run_id"]
        runs = RunStore(db).list()
        assert len(runs) == 1
    finally:
        db.close()


def test_submit_idempotency_same_key_different_request_conflicts(tmp_path: Path) -> None:
    from conflux.workbench.jobs import IdempotencyConflict

    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    manager.submit("query A", {"depth": "quick"}, idempotency_key="key-conflict")
    with pytest.raises(IdempotencyConflict):
        manager.submit("query B", {"depth": "quick"}, idempotency_key="key-conflict")


def test_submit_without_key_creates_distinct_runs(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    first = manager.submit("no key", {"depth": "quick"})
    second = manager.submit("no key", {"depth": "quick"})
    assert first["run_id"] != second["run_id"]

    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        assert len(JobQueue(db).list(kind=RESEARCH_JOB_KIND)) == 2
    finally:
        db.close()


def test_submit_queue_position_and_active_count(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    r1 = manager.submit("first", {"depth": "quick"})
    r2 = manager.submit("second", {"depth": "quick"})
    # active_count includes the job being submitted itself.
    assert r1["active_count"] == 1
    assert r2["active_count"] == 2
    assert r1["queue_position"] == 0
    assert r2["queue_position"] == 1

    mgr2 = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    r3 = mgr2.submit("third", {"depth": "quick"})
    assert r3["queue_position"] == 2
    assert r3["active_count"] == 3


def test_submit_backpressure_at_job_limit(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    manager.MAX_JOBS = 2
    manager.submit("one", {"depth": "quick"})
    manager.submit("two", {"depth": "quick"})
    with pytest.raises(RuntimeError, match="Job limit reached"):
        manager.submit("three", {"depth": "quick"})


def test_submit_idempotency_concurrent_duplicates_produce_single_run(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    barrier = threading.Barrier(20)
    run_ids: list[str] = []
    errors: list[str] = []
    lock = threading.Lock()

    def submit_duplicate() -> None:
        barrier.wait()
        try:
            result = manager.submit(
                "concurrent duplicate", {"depth": "quick"}, idempotency_key="key-concurrent"
            )
            with lock:
                run_ids.append(result["run_id"])
        except Exception as exc:  # pragma: no cover - failure diagnostics only
            with lock:
                errors.append(type(exc).__name__)

    threads = [threading.Thread(target=submit_duplicate) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(run_ids) == 20
    assert len(set(run_ids)) == 1

    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        jobs = JobQueue(db).list(kind=RESEARCH_JOB_KIND)
        assert len(jobs) == 1
        assert jobs[0]["run_id"] == run_ids[0]
        assert len(RunStore(db).list()) == 1
    finally:
        db.close()

