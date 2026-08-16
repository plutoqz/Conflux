"""M3 durable Workbench research-query jobs and run-local configuration."""

from __future__ import annotations

import copy
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


# --- P1.3: frozen run manifest + restart credentials ---


def test_submit_records_frozen_run_manifest_without_secrets(tmp_path: Path) -> None:
    manager = JobManager(db_path=tmp_path / "conflux.db", start_worker=False)
    result = manager.submit(
        "frozen query",
        {
            "depth": "quick",
            "model": "test-model-x",
            "base_url": "https://example.invalid/v1",
            "api_key": "reasoning-secret-abc",
            "embedding_api_key": "embedding-secret-xyz",
        },
    )

    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        metadata = dict((RunStore(db).get(result["run_id"]) or {}).get("metadata") or {})
    finally:
        db.close()

    manifest = dict(metadata.get("run_manifest") or {})
    assert manifest.get("schema") == "conflux.run_manifest.v1"
    revision = str(manifest.get("code_revision") or "")
    assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
    assert manifest.get("semantic_hash")
    assert manifest.get("model_revision") is None
    assert manifest.get("model_revision_verified") is False
    assert manifest.get("model_revision_unverified") is True
    assert manifest.get("roles", {}).get("planner", {}).get("model") == "test-model-x"
    assert manifest.get("roles", {}).get("planner", {}).get("provider") == "openai_compatible"

    credentials = {str(item.get("ref")): item for item in manifest.get("credentials") or []}
    assert credentials["workbench_payload:api_key"]["policy"] == "fail_closed"
    assert credentials["workbench_payload:embedding_api_key"]["policy"] == "fail_closed"

    serialized = json.dumps(metadata, ensure_ascii=False)
    assert "reasoning-secret-abc" not in serialized
    assert "embedding-secret-xyz" not in serialized


def test_restart_fails_closed_when_payload_credentials_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    calls: list[int] = []

    def spy_query(*args, **kwargs):
        calls.append(1)
        return _fake_query_command(*args, **kwargs)

    monkeypatch.setattr(cli, "query_command", spy_query)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit(
        "temporary key run",
        {"depth": "quick", "model": "override-model", "api_key": "temporary-key-123"},
    )["run_id"]

    # 重启模拟：新 manager 内存里没有临时密钥，必须 fail-closed，不得静默回退。
    worker = JobManager(db_path=db_path, poll_interval=0.02)
    status = _wait_for_status(worker, run_id, {"failed"})
    worker.close()

    assert calls == []
    assert status["has_report"] is False
    assert "credential_unavailable_after_restart" in status["error"]
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["schema_version"] == "conflux.research_failure.v1"
    assert "credential_unavailable_after_restart" in diagnostic["error"]
    assert diagnostic["recovery"]["retryable"] is False

    db = SQLiteDatabase(db_path).connect()
    try:
        queued = JobQueue(db).get(run_id)
        assert queued is not None and queued["status"] == "failed"
        events = EventStore(db).list(run_id=run_id)
        assert any(str(item.get("stage")) == "credential_recovery" for item in events)
    finally:
        db.close()


def test_restart_resolves_env_credential_ref_and_runs(tmp_path: Path, monkeypatch) -> None:
    from conflux import __main__ as cli

    monkeypatch.setattr(cli, "query_command", _fake_query_command)
    monkeypatch.setenv("CONFLUX_MODELS__FLASH__API_KEY", "env-key-value")
    config._config = None
    try:
        db_path = tmp_path / "conflux.db"
        submitter = JobManager(db_path=db_path, start_worker=False)
        run_id = submitter.submit("env key run", {"depth": "quick"})["run_id"]

        db = SQLiteDatabase(db_path).connect()
        try:
            metadata = dict((RunStore(db).get(run_id) or {}).get("metadata") or {})
        finally:
            db.close()
        manifest = dict(metadata.get("run_manifest") or {})
        refs = [str(item.get("ref")) for item in manifest.get("credentials") or []]
        assert "env:CONFLUX_MODELS__FLASH__API_KEY" in refs
        assert "env-key-value" not in json.dumps(manifest, ensure_ascii=False)

        # 重启后 env 引用仍可解析 → 正常恢复执行。
        worker = JobManager(db_path=db_path, poll_interval=0.02)
        status = _wait_for_status(worker, run_id, {"completed_diagnostic"})
        worker.close()
        assert status["status"] == "completed_diagnostic"
        assert "credential_unavailable" not in status["error"]
    finally:
        config._config = None


def test_restart_detects_frozen_config_drift_and_fails_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from conflux import __main__ as cli

    calls: list[int] = []

    def spy_query(*args, **kwargs):
        calls.append(1)
        return _fake_query_command(*args, **kwargs)

    monkeypatch.setattr(cli, "query_command", spy_query)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("config drift", {"depth": "quick"})["run_id"]

    # 漂移：提交后把 quick 档 planner 的 preset 换掉（不触及任何密钥）。
    drifted = copy.deepcopy(config.load())
    drifted["research"]["profiles"]["quick"]["planner_model"] = "ds_strong"
    monkeypatch.setattr(config, "_config", drifted)

    worker = JobManager(db_path=db_path, poll_interval=0.02)
    status = _wait_for_status(worker, run_id, {"failed"})
    worker.close()

    assert calls == []
    assert status["has_report"] is False
    assert "frozen_config_mismatch" in status["error"]
    assert "credential_unavailable_after_restart" not in status["error"]
# --- P1.4: 所有终态结构化诊断（conflux.research_failure.v1 扩展） ---


def test_lease_overrun_persists_failure_diagnostic_and_terminal(tmp_path: Path) -> None:
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit(
        "lease overrun probe",
        {"depth": "quick", "output_dir": str(tmp_path / "reports")},
    )["run_id"]

    # 两次死 worker claim 耗尽 max_attempts(2) 后租约过期 → 终态 lease 超限。
    db = SQLiteDatabase(db_path).connect()
    try:
        queue = JobQueue(db, lease_seconds=0.01)
        assert queue.claim("dead-worker-1", kind=RESEARCH_JOB_KIND) is not None
        time.sleep(0.03)
        assert queue.claim("dead-worker-2", kind=RESEARCH_JOB_KIND) is not None
        time.sleep(0.03)
    finally:
        db.close()

    worker = JobManager(db_path=db_path, poll_interval=0.02)
    status = _wait_for_status(worker, run_id, {"failed"})
    worker.close()

    assert "lease" in status["error"]
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["schema_version"] == "conflux.research_failure.v1"
    assert diagnostic["failure_code"] == "lease_overrun"
    assert diagnostic["failure_stage"] == "lease"
    assert diagnostic["run_id"] == run_id
    assert diagnostic["query"] == "lease overrun probe"
    assert len(diagnostic["code_revision"]) == 40
    assert diagnostic["input_config_hash"]
    assert diagnostic["preserved_artifacts"] == {}

    db = SQLiteDatabase(db_path).connect()
    try:
        queued = JobQueue(db).get(run_id)
        run = RunStore(db).get(run_id)
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert queued["status"] == "failed"
    assert run["status"] == "failed"
    assert any(e["stage"] == "lease_overrun" and e["status"] == "failed" for e in events)
    # 终态与诊断引用同一 RunStore 行可见：status 与 artifacts 诊断引用同时落地。
    metadata = dict(run.get("metadata") or {})
    assert metadata["public_status"] == "failed"
    assert metadata["artifacts"]["diagnostic_json_path"]


def test_user_cancel_persists_structured_diagnostic(tmp_path: Path, monkeypatch) -> None:
    from conflux import __main__ as cli

    entered = threading.Event()
    release = threading.Event()

    def cancellable_query(query: str, **kwargs):
        entered.set()
        assert release.wait(2.0)
        kwargs["should_stop"]()
        return {"_delivery_status": "diagnostic_only", "_run_summary": {"mode": "answer_first"}}

    monkeypatch.setattr(cli, "query_command", cancellable_query)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "cancel diagnostic", {"depth": "quick", "output_dir": str(output_dir)}
    )["run_id"]
    assert entered.wait(2.0)
    assert manager.cancel(run_id) is True
    release.set()
    status = _wait_for_status(manager, run_id, {"cancelled"})
    manager.close()

    assert status["status"] == "cancelled"
    assert status["cancel_reason"] == "user"
    # 取消终态立即生效；结构化诊断由 worker 在同一终态事务内补齐 —— 轮询等待。
    diagnostic_path = ""
    deadline = time.time() + 5.0
    while time.time() < deadline:
        status = manager.get(run_id)
        diagnostic_path = str((status or {}).get("artifacts", {}).get("diagnostic_json_path") or "")
        if diagnostic_path:
            break
        time.sleep(0.02)
    assert diagnostic_path, "取消终态必须补齐结构化诊断引用"
    diagnostic = json.loads(Path(diagnostic_path).read_text(encoding="utf-8"))
    assert diagnostic["failure_code"] == "user_cancelled"
    assert diagnostic["failure_stage"] == "user_cancel"
    assert diagnostic["status"] == "cancelled"
    assert diagnostic["recovery"]["retryable"] is False
    assert diagnostic["run_id"] == run_id
    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert any(e["stage"] == "user_cancel" and e["status"] == "cancelled" for e in events)


def test_system_deadline_persists_structured_diagnostic(tmp_path: Path, monkeypatch) -> None:
    from conflux import __main__ as cli
    from conflux.workbench.jobs import _JobTimedOut

    def deadline_query(*_args, **_kwargs):
        raise _JobTimedOut("研究任务超过 180 秒档位时限")

    monkeypatch.setattr(cli, "query_command", deadline_query)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "deadline probe", {"depth": "quick", "output_dir": str(output_dir)}
    )["run_id"]
    status = _wait_for_status(manager, run_id, {"timed_out", "timed_out_with_report"})
    manager.close()

    assert status["status"].startswith("timed_out")
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["failure_code"] == "system_deadline"
    assert diagnostic["failure_stage"] == "system_deadline"
    assert diagnostic["status"] == "timed_out"
    assert diagnostic["recovery"]["retryable"] is True
    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert any(e["stage"] == "system_deadline" for e in events)


def test_config_build_failure_persists_structured_diagnostic(
    tmp_path: Path, monkeypatch
) -> None:
    from conflux import __main__ as cli

    def config_failure(*_args, **_kwargs):
        raise SystemExit(2)

    monkeypatch.setattr(cli, "query_command", config_failure)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "config probe", {"depth": "quick", "output_dir": str(output_dir)}
    )["run_id"]
    status = _wait_for_status(manager, run_id, {"failed"})
    manager.close()

    assert status["status"] == "failed"
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["failure_code"] == "config_build_failure"
    assert diagnostic["failure_stage"] == "config_build"
    assert diagnostic["recovery"]["retryable"] is False
    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert any(e["stage"] == "config_build" and e["status"] == "failed" for e in events)


def test_model_build_failure_persists_structured_diagnostic(
    tmp_path: Path, monkeypatch
) -> None:
    from conflux import __main__ as cli

    def model_failure(*_args, **_kwargs):
        raise ValueError("openai_compatible 模型构建失败：无法解析 base_url")

    monkeypatch.setattr(cli, "query_command", model_failure)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "model probe", {"depth": "quick", "output_dir": str(output_dir)}
    )["run_id"]
    status = _wait_for_status(manager, run_id, {"failed"})
    manager.close()

    assert status["status"] == "failed"
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["failure_code"] == "model_build_failure"
    assert diagnostic["failure_stage"] == "model_build"
    assert diagnostic["error_type"] == "ValueError"
    assert diagnostic["recovery"]["retryable"] is False


def test_final_commit_failure_never_publishes_completed(
    tmp_path: Path, monkeypatch
) -> None:
    from conflux import __main__ as cli
    import conflux.report as report_module

    def almost_done_query(query: str, **kwargs):
        state = {
            "query": query,
            "_pipeline_stage": "completed",
            "_run_status": "completed",
            "_delivery_status": "report_ready",
            "_run_summary": {"mode": "answer_first"},
            "_source_statuses": {},
            "_audit_metrics": {},
            "final_answer": "draft answer content",
        }
        kwargs["should_stop"]()
        kwargs["on_graph_state"](state, [])
        kwargs["should_stop"]()
        return state

    def broken_write(*_args, **_kwargs):
        raise OSError("disk full during final artifact commit")

    monkeypatch.setattr(cli, "query_command", almost_done_query)
    monkeypatch.setattr(report_module, "write_staged_markdown_report", broken_write)
    output_dir = tmp_path / "reports"
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit(
        "final commit probe", {"depth": "quick", "output_dir": str(output_dir)}
    )["run_id"]
    status = _wait_for_status(manager, run_id, {"failed"})
    manager.close()

    assert status["status"] == "failed"
    assert status["has_report"] is False
    assert "final_commit_failure" in status["error"]
    diagnostic = json.loads(
        Path(status["artifacts"]["diagnostic_json_path"]).read_text(encoding="utf-8")
    )
    assert diagnostic["failure_code"] == "final_commit_failure"
    assert diagnostic["failure_stage"] == "final_commit"
    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        queued = JobQueue(db).get(run_id)
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert queued["status"] == "failed"
    assert any(e["stage"] == "final_commit" and e["status"] == "failed" for e in events)


def test_worker_init_failure_is_observable_without_corrupting_jobs(
    tmp_path: Path, monkeypatch
) -> None:
    from conflux import __main__ as cli

    monkeypatch.setattr(cli, "query_command", _fake_query_command)
    db_path = tmp_path / "conflux.db"
    submitter = JobManager(db_path=db_path, start_worker=False)
    run_id = submitter.submit("survives worker init failure", {"depth": "quick"})["run_id"]

    # 补丁必须在 worker 线程启动前生效（否则首轮 claim 已经成功）。
    worker = JobManager(db_path=db_path, poll_interval=0.02, start_worker=False)
    original_claim = worker._claim_next
    state_box = {"calls": 0}

    def flaky_claim():
        state_box["calls"] += 1
        if state_box["calls"] <= 4:
            raise RuntimeError("worker bootstrap: database bootstrap failed")
        return original_claim()

    monkeypatch.setattr(worker, "_claim_next", flaky_claim)
    worker._worker_thread = threading.Thread(target=worker._worker_loop, daemon=True)
    worker._worker_thread.start()
    status = _wait_for_status(worker, run_id, {"completed_diagnostic"})
    worker.close()

    # 任务不受 worker 初始化故障影响：保持 pending 直到恢复并正常完成。
    assert status["status"] == "completed_diagnostic"
    deadline = time.time() + 2.0
    while time.time() < deadline and worker.worker_error:
        time.sleep(0.02)
    assert worker.worker_error == ""
    assert worker.worker_consecutive_failures == 0
    db = SQLiteDatabase(db_path).connect()
    try:
        events = EventStore(db).list(run_id="")
    finally:
        db.close()
    init_events = [
        event for event in events if event["stage"] == "worker_init" and event["status"] == "failed"
    ]
    assert len(init_events) >= 1
    metadata = dict(init_events[0].get("metadata") or {})
    assert metadata.get("failure_code") == "worker_init_failure"
    assert "bootstrap" in str(metadata.get("error") or "")


def test_terminal_and_diagnostic_reference_share_one_transaction(
    tmp_path: Path, monkeypatch
) -> None:
    """终态写入与诊断引用原子性：任一写入失败时全部回滚，不出现半提交终态。"""
    from conflux.workbench.jobs import _job_from_metadata, _persist_terminal

    db_path = tmp_path / "conflux.db"
    manager = JobManager(db_path=db_path, start_worker=False)
    run_id = manager.submit("atomic terminal", {"depth": "quick"})["run_id"]

    db = SQLiteDatabase(db_path).connect()
    try:
        queue = JobQueue(db, lease_seconds=30.0)
        run_store = RunStore(db)
        event_store = EventStore(db)
        run_before = run_store.get(run_id)
        claimed = queue.claim(manager._worker_id, kind=RESEARCH_JOB_KIND)
        assert claimed is not None
        job = _job_from_metadata(
            run_id, dict((run_store.get(run_id) or {}).get("metadata") or {})
        )
        job.status = "failed"
        job.error = "probe failure"
        job.current_stage = "execution"
        job.ended_at = time.time()
        job.artifacts["diagnostic_json_path"] = str(tmp_path / "probe.diagnostic.json")

        original_append = EventStore.append

        def failing_append(self, event, *, commit=True):
            raise RuntimeError("events table write failure")

        monkeypatch.setattr(EventStore, "append", failing_append)
        try:
            with pytest.raises(RuntimeError):
                _persist_terminal(
                    db,
                    queue,
                    run_store,
                    event_store,
                    run_id,
                    job,
                    worker_id=manager._worker_id,
                    terminal="failed",
                    error="probe failure",
                    event=TraceEvent(
                        stage="execution",
                        status="failed",
                        summary="probe",
                        run_id=run_id,
                        thread_id=run_id,
                    ),
                )
        finally:
            monkeypatch.setattr(EventStore, "append", original_append)

        # 回滚验证：queue 行、run 行、事件行都不得出现终态。
        assert JobQueue(db).get(run_id)["status"] == "running"
        run_after = RunStore(db).get(run_id)
        assert run_after["status"] == run_before["status"]
        assert run_after["metadata"] == run_before["metadata"]
        assert EventStore(db).list(run_id=run_id) == []
    finally:
        db.close()


def test_completed_diagnostic_run_still_has_no_failure_diagnostic(
    tmp_path: Path, monkeypatch
) -> None:
    """正常完成（含 completed_diagnostic）不产生失败诊断 artifact。"""
    from conflux import __main__ as cli

    monkeypatch.setattr(cli, "query_command", _fake_query_command)
    manager = JobManager(db_path=tmp_path / "conflux.db", poll_interval=0.02)
    run_id = manager.submit("clean completion", {"depth": "quick"})["run_id"]
    status = _wait_for_status(manager, run_id, {"completed_diagnostic"})
    manager.close()

    assert status["status"] == "completed_diagnostic"
    assert "diagnostic_json_path" not in status["artifacts"]
    db = SQLiteDatabase(tmp_path / "conflux.db").connect()
    try:
        events = EventStore(db).list(run_id=run_id)
    finally:
        db.close()
    assert any(e["stage"] == "final_commit" and e["status"] == "completed" for e in events)


