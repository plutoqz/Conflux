"""Durable Workbench research-query jobs backed by the M3 SQLite stores."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conflux import config
from conflux.adapters.sqlite_store import (
    CheckpointStore,
    EventStore,
    JobQueue,
    RunStore,
    SQLiteDatabase,
)
from conflux.core.contracts import RunContext
from conflux.core.runtime_home import database_path
from conflux.trace import TraceEvent, new_run_id


RESEARCH_JOB_KIND = "research_query"
_SECRET_FIELDS = {
    "api_key",
    "embedding_api_key",
    "serpapi_api_key",
    "bing_api_key",
    "google_api_key",
    "password",
    "token",
}


class _JobCancelled(RuntimeError):
    pass


class _JobTimedOut(RuntimeError):
    pass


class _EventLog:
    """Legacy in-memory event log retained only for narrow helper tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict | None] = []
        self._closed = False
        self._notify = threading.Condition(self._lock)

    def append(self, event: dict | None) -> int:
        with self._lock:
            if self._closed:
                return -1
            self._events.append(event)
            if event is None:
                self._closed = True
            self._notify.notify_all()
            return len(self._events) - 1

    def read_from(self, cursor: int, timeout: float = 30.0) -> tuple[list[dict | None], int, bool]:
        with self._lock:
            while cursor >= len(self._events) and not self._closed:
                if not self._notify.wait(timeout):
                    break
            if cursor >= len(self._events):
                return [], cursor, self._closed
            batch = self._events[cursor:]
            return batch, len(self._events), self._closed


@dataclass
class ResearchJob:
    run_id: str
    query: str
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    status: str = "pending"
    timeout_seconds: int = 300
    deadline_at: float = 0.0
    commit_reserve_seconds: float = 20.0
    project_id: str = ""
    work_item_id: str = ""
    final_answer: str = ""
    has_report: bool = False
    source_statuses: dict[str, str] = field(default_factory=dict)
    factcheck_status: str = ""
    pipeline: str = ""
    delivery_status: str = ""
    quality: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    error: str = ""
    current_stage: str = ""
    progress: dict[str, str] = field(default_factory=dict)
    cancel_reason: str = ""
    warnings: list[str] = field(default_factory=list)
    thread: threading.Thread | None = None
    _cancel_flag: threading.Event = field(default_factory=threading.Event)
    _event_log: _EventLog = field(default_factory=_EventLog)

    def __post_init__(self) -> None:
        if self.deadline_at <= 0:
            self.deadline_at = self.started_at + max(1, self.timeout_seconds)
        self.has_report = bool(
            (self.has_report or self.final_answer)
            and self.delivery_status != "diagnostic_only"
        )

    @property
    def active(self) -> bool:
        return self.status in ("pending", "running")


def _deadline_exceeded(job: ResearchJob) -> bool:
    return time.time() >= job.deadline_at


def _enforce_job_stop(job: ResearchJob, started_at: float | None = None) -> None:
    if job._cancel_flag.is_set():
        if job.cancel_reason == "timeout":
            raise _JobTimedOut(
                f"系统在 {job.timeout_seconds} 秒档位时限后自动终止研究任务"
            )
        raise _JobCancelled("用户取消了研究任务")
    if _deadline_exceeded(job):
        job.cancel_reason = "timeout"
        raise _JobTimedOut(f"研究任务超过 {job.timeout_seconds} 秒档位时限")


def _finish_job(
    job: ResearchJob,
    status: str,
    error: str,
    *,
    preserve_report: bool = True,
) -> None:
    job.ended_at = time.time()
    has_report = bool(
        preserve_report
        and (job.has_report or job.final_answer or job.artifacts.get("markdown_path"))
    )
    job.has_report = has_report
    if status == "timed_out" and has_report:
        job.status = "timed_out_with_report"
        warning = "后续研究或核验超时，已保留当前报告。"
    else:
        job.status = status
        warning = ""
    job.error = str(error)
    if warning:
        job.warnings.append(warning)
    elif not has_report:
        job.error = f"{error}，未生成正式报告。"


def _finish_without_report(job: ResearchJob, status: str, error: str) -> None:
    _finish_job(job, status, error, preserve_report=True)


def _capture_report_snapshot(
    job: ResearchJob,
    state: dict[str, Any],
    output_dir: str,
    *,
    stage: str,
) -> None:
    from conflux.report import write_staged_markdown_report

    answer = str(state.get("final_answer") or state.get("_verified_answer") or "")
    if not answer.strip():
        return
    job.final_answer = answer
    delivery_status = str(state.get("_delivery_status") or "")
    if delivery_status:
        job.delivery_status = delivery_status
    job.has_report = True
    job.factcheck_status = str(state.get("_factcheck_status") or job.factcheck_status)
    try:
        path = write_staged_markdown_report(
            job.query,
            state,
            output_dir,
            run_id=job.run_id,
            stage=stage,
        )
    except Exception as exc:
        job.warnings.append(
            f"{stage} report snapshot failed: {type(exc).__name__}: {exc}"
        )
        return
    key = "verified_markdown_path" if stage == "verified" else "draft_markdown_path"
    job.artifacts[key] = str(path.resolve())
    job.artifacts["markdown_path"] = str(path.resolve())


def _persist_trace_snapshot(job: ResearchJob, events: list[Any], output_dir: str) -> None:
    if not events:
        return
    from conflux.trace import write_trace_jsonl

    path = Path(output_dir) / f"{job.run_id}.trace.jsonl"
    try:
        write_trace_jsonl(events, path)
    except Exception as exc:
        job.warnings.append(f"trace snapshot failed: {type(exc).__name__}: {exc}")
        return
    job.artifacts["trace_path"] = str(path.resolve())


def _state_warnings(state: dict[str, Any]) -> list[str]:
    findings = state.get("_factcheck_findings") or {}
    if not isinstance(findings, dict):
        findings = {}
    candidates = [
        state.get("_synthesis_error"),
        findings.get("verifier_error"),
        findings.get("recheck_verifier_error"),
        findings.get("revision_error"),
    ]
    warnings = [str(value).strip() for value in candidates if str(value or "").strip()]
    factcheck_status = str(state.get("_factcheck_status") or "")
    if factcheck_status and factcheck_status != "passed":
        warnings.append(f"FactCheck status: {factcheck_status}")
    quality = state.get("_audit_metrics") or {}
    failed_sections = int(quality.get("sections_failed") or 0) if isinstance(quality, dict) else 0
    total_sections = int(quality.get("total_sections") or 0) if isinstance(quality, dict) else 0
    if failed_sections:
        warnings.append(f"{failed_sections}/{total_sections} 个扩展问题未完成")
    return list(dict.fromkeys(warnings))


def _sanitize_payload(value: Any, *, key: str = "") -> Any:
    normalized_key = key.casefold()
    if normalized_key in _SECRET_FIELDS or normalized_key.endswith("_api_key"):
        return None
    if isinstance(value, dict):
        return {
            str(item_key): sanitized
            for item_key, item_value in value.items()
            if (sanitized := _sanitize_payload(item_value, key=str(item_key))) is not None
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    return value


def _job_metadata(job: ResearchJob) -> dict[str, Any]:
    return {
        "kind": RESEARCH_JOB_KIND,
        "query": job.query,
        "public_status": job.status,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "timeout_seconds": job.timeout_seconds,
        "deadline_at": job.deadline_at,
        "commit_reserve_seconds": job.commit_reserve_seconds,
        "project_id": job.project_id,
        "work_item_id": job.work_item_id,
        "final_answer": job.final_answer,
        "source_statuses": job.source_statuses,
        "factcheck_status": job.factcheck_status,
        "pipeline": job.pipeline,
        "delivery_status": job.delivery_status,
        "quality": job.quality,
        "artifacts": job.artifacts,
        "error": job.error,
        "current_stage": job.current_stage,
        "progress": job.progress,
        "cancel_reason": job.cancel_reason,
        "has_report": job.has_report,
        "warnings": job.warnings,
    }


def _job_from_metadata(run_id: str, metadata: dict[str, Any]) -> ResearchJob:
    return ResearchJob(
        run_id=run_id,
        query=str(metadata.get("query") or ""),
        started_at=float(metadata.get("started_at") or time.time()),
        ended_at=metadata.get("ended_at"),
        status=str(metadata.get("public_status") or "pending"),
        timeout_seconds=max(1, int(metadata.get("timeout_seconds") or 300)),
        deadline_at=float(metadata.get("deadline_at") or 0.0),
        commit_reserve_seconds=float(metadata.get("commit_reserve_seconds") or 20.0),
        project_id=str(metadata.get("project_id") or ""),
        work_item_id=str(metadata.get("work_item_id") or ""),
        final_answer=str(metadata.get("final_answer") or ""),
        has_report=bool(metadata.get("has_report")),
        source_statuses=dict(metadata.get("source_statuses") or {}),
        factcheck_status=str(metadata.get("factcheck_status") or ""),
        pipeline=str(metadata.get("pipeline") or ""),
        delivery_status=str(metadata.get("delivery_status") or ""),
        quality=dict(metadata.get("quality") or {}),
        artifacts={str(k): str(v) for k, v in (metadata.get("artifacts") or {}).items()},
        error=str(metadata.get("error") or ""),
        current_stage=str(metadata.get("current_stage") or ""),
        progress={str(k): str(v) for k, v in (metadata.get("progress") or {}).items()},
        cancel_reason=str(metadata.get("cancel_reason") or ""),
        warnings=[str(item) for item in (metadata.get("warnings") or [])],
    )


def _public_status(job: ResearchJob) -> dict[str, Any]:
    full_answer = job.final_answer or ""
    answer_len = len(full_answer)
    return {
        "run_id": job.run_id,
        "query": job.query,
        "status": job.status,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "timeout_seconds": job.timeout_seconds,
        "deadline_at": job.deadline_at,
        "commit_reserve_seconds": job.commit_reserve_seconds,
        "project_id": job.project_id,
        "work_item_id": job.work_item_id,
        "final_answer": full_answer[:4000],
        "final_answer_truncated": answer_len > 4000,
        "final_answer_total_length": answer_len,
        "source_statuses": job.source_statuses,
        "factcheck_status": job.factcheck_status,
        "pipeline": job.pipeline,
        "delivery_status": job.delivery_status,
        "quality": dict(job.quality),
        "artifacts": dict(job.artifacts),
        "report_md_path": str(job.artifacts.get("markdown_path") or ""),
        "error": job.error,
        "current_stage": job.current_stage,
        "progress": dict(job.progress),
        "cancel_reason": job.cancel_reason,
        "has_report": job.has_report,
        "warning": " ".join(job.warnings),
        "warnings": list(job.warnings),
    }


class JobManager:
    """Persistent adapter for Workbench research-query jobs."""

    MAX_JOBS = 100

    def __init__(
        self,
        ttl_seconds: float = 3600.0,
        *,
        db_path: str | Path | None = None,
        start_worker: bool = True,
        poll_interval: float = 0.25,
        lease_seconds: float = 30.0,
    ) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, ResearchJob] = {}
        self._ttl = ttl_seconds
        self._db_path = Path(db_path or database_path()).resolve()
        self._poll_interval = max(0.05, poll_interval)
        self._lease_seconds = max(3.0, lease_seconds)
        self._worker_id = f"workbench-query-{uuid.uuid4().hex[:12]}"
        self._last_worker_error = ""
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._secrets: dict[str, dict[str, Any]] = {}
        db = self._database()
        db.close()
        self._worker_thread: threading.Thread | None = None
        if start_worker:
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _database(self) -> SQLiteDatabase:
        db = SQLiteDatabase(self._db_path).connect()
        db.bootstrap_schema()
        return db

    def submit(self, query: str, payload: dict[str, Any], *, run_id: str | None = None) -> dict[str, Any]:
        run_id = run_id or new_run_id()
        depth = str(payload.get("depth") or "standard")
        try:
            from conflux.research_modes import resolve_research_profile

            profile = resolve_research_profile(depth)
            timeout_seconds = profile.timeout_seconds
            commit_reserve_seconds = profile.commit_reserve_seconds
        except Exception:
            timeout_seconds = 300
            commit_reserve_seconds = 20
        started_at = time.time()
        timeout_seconds = max(1, int(timeout_seconds))
        job = ResearchJob(
            run_id=run_id,
            query=query,
            started_at=started_at,
            timeout_seconds=timeout_seconds,
            deadline_at=started_at + timeout_seconds,
            commit_reserve_seconds=commit_reserve_seconds,
            project_id=str(payload.get("project_id") or ""),
            work_item_id=str(payload.get("work_item_id") or ""),
        )
        persisted_payload = _sanitize_payload(dict(payload))
        secrets = {
            key: value
            for key, value in payload.items()
            if key.casefold() in _SECRET_FIELDS or key.casefold().endswith("_api_key")
        }
        db = self._database()
        try:
            queue = JobQueue(db, lease_seconds=self._lease_seconds)
            active = sum(
                1 for item in queue.list(kind=RESEARCH_JOB_KIND, limit=self.MAX_JOBS + 1)
                if item["status"] in {"pending", "running"}
            )
            if active >= self.MAX_JOBS:
                raise RuntimeError(f"Job limit reached ({self.MAX_JOBS}). Wait for active jobs to finish.")
            RunStore(db).create_run(
                run_id=run_id,
                workspace=str(config.PROJECT_ROOT),
                status="pending",
                thread_id=run_id,
                metadata=_job_metadata(job),
            )
            queue.enqueue(
                RESEARCH_JOB_KIND,
                {
                    "query": query,
                    "payload": persisted_payload,
                    "started_at": started_at,
                    "timeout_seconds": timeout_seconds,
                    "deadline_at": job.deadline_at,
                    "commit_reserve_seconds": commit_reserve_seconds,
                },
                job_id=run_id,
                run_id=run_id,
                max_attempts=2,
            )
        finally:
            db.close()
        if secrets:
            with self._lock:
                self._secrets[run_id] = secrets
        self._wake.set()
        return {
            "run_id": run_id,
            "status": "pending",
            "events_url": f"/api/query/jobs/{run_id}/events",
            "status_url": f"/api/query/jobs/{run_id}",
            "timeout_seconds": job.timeout_seconds,
            "deadline_at": job.deadline_at,
            "commit_reserve_seconds": job.commit_reserve_seconds,
        }

    def get(self, run_id: str) -> dict[str, Any] | None:
        db = self._database()
        try:
            queued = JobQueue(db, lease_seconds=self._lease_seconds).get(run_id)
            run = RunStore(db).get(run_id)
        finally:
            db.close()
        if queued is None or run is None:
            legacy = self._jobs.get(run_id)
            return _public_status(legacy) if legacy else None
        metadata = dict(run.get("metadata") or {})
        metadata.update(queued.get("result") or {})
        job = _job_from_metadata(run_id, metadata)
        if job.status in {"pending", "running"}:
            job.status = str(queued.get("status") or job.status)
        if queued.get("error") and not job.error:
            job.error = str(queued["error"])
        return _public_status(job)

    def cancel(self, run_id: str, *, reason: str = "user") -> bool:
        db = self._database()
        try:
            queue = JobQueue(db, lease_seconds=self._lease_seconds)
            cancelled = queue.cancel(run_id)
            if cancelled:
                run_store = RunStore(db)
                run = run_store.get(run_id) or {}
                metadata = dict(run.get("metadata") or {})
                metadata.update(
                    public_status="cancelled",
                    cancel_reason="timeout" if reason == "timeout" else "user",
                    ended_at=time.time(),
                )
                run_store.update_metadata(run_id, metadata, status="cancelled")
                EventStore(db).append(
                    TraceEvent(
                        stage="job_cancelled",
                        status="cancelled",
                        elapsed_ms=0.0,
                        summary="Research job cancellation persisted",
                        run_id=run_id,
                        thread_id=run_id,
                        metadata={"reason": metadata["cancel_reason"]},
                    )
                )
        finally:
            db.close()
        if cancelled:
            with self._lock:
                self._secrets.pop(run_id, None)
            self._wake.set()
            return True
        with self._lock:
            legacy = self._jobs.get(run_id)
            if legacy is None or not legacy.active:
                return False
            legacy.cancel_reason = "timeout" if reason == "timeout" else "user"
            legacy._cancel_flag.set()
            return True

    def list(self, limit: int = 20, *, project_id: str | None = None) -> list[dict[str, Any]]:
        db = self._database()
        try:
            queued = JobQueue(db, lease_seconds=self._lease_seconds).list(
                kind=RESEARCH_JOB_KIND,
                limit=self.MAX_JOBS,
            )
            runs = {item["run_id"]: item for item in RunStore(db).list(limit=self.MAX_JOBS)}
        finally:
            db.close()
        result = []
        for item in sorted(queued, key=lambda value: float(value["created_at"]), reverse=True)[:limit]:
            run = runs.get(item["run_id"], {})
            metadata = dict(run.get("metadata") or {})
            metadata.update(item.get("result") or {})
            if project_id is not None and str(metadata.get("project_id") or "") != project_id:
                continue
            result.append(
                {
                    "run_id": item["run_id"],
                    "query": str(metadata.get("query") or "")[:200],
                    "status": str(metadata.get("public_status") or item["status"]),
                    "started_at": metadata.get("started_at", item["created_at"]),
                    "ended_at": metadata.get("ended_at"),
                    "project_id": str(metadata.get("project_id") or ""),
                    "work_item_id": str(metadata.get("work_item_id") or ""),
                }
            )
        return result

    def events(self, run_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        db = self._database()
        try:
            return EventStore(db).list(run_id=run_id, after_id=after_id, limit=limit)
        finally:
            db.close()

    def event_log(self, run_id: str) -> None:
        return None

    def close(self) -> None:
        self._stop.set()
        self._wake.set()

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                claimed = self._claim_next()
                if claimed:
                    payload = dict(claimed.get("payload") or {})
                    if int(claimed.get("attempts") or 0) > 1:
                        self._record_resume(claimed)
                    self._execute(
                        str(claimed["run_id"]),
                        str(payload.get("query") or ""),
                        dict(payload.get("payload") or {}),
                    )
                    continue
                self._last_worker_error = ""
            except Exception as exc:
                self._last_worker_error = f"{type(exc).__name__}: {exc}"
            self._wake.wait(self._poll_interval)
            self._wake.clear()

    def _claim_next(self) -> dict[str, Any] | None:
        db = self._database()
        try:
            queue = JobQueue(db, lease_seconds=self._lease_seconds)
            exhausted = queue.expire_exhausted(kind=RESEARCH_JOB_KIND)
            for item in exhausted:
                RunStore(db).update_metadata(
                    item["run_id"],
                    {
                        "public_status": "failed",
                        "error": str(item.get("error") or "lease expired after max attempts"),
                        "ended_at": time.time(),
                    },
                    status="failed",
                )
            claimed = queue.claim(self._worker_id, kind=RESEARCH_JOB_KIND)
            if claimed and self._restore_terminal_checkpoint(db, claimed):
                return None
            return claimed
        finally:
            db.close()

    def _restore_terminal_checkpoint(self, db: SQLiteDatabase, claimed: dict[str, Any]) -> bool:
        checkpoint = CheckpointStore(db).load(str(claimed["run_id"]))
        terminal = dict((checkpoint or {}).get("terminal_result") or {})
        if not terminal:
            return False
        queue = JobQueue(db, lease_seconds=self._lease_seconds)
        completed = queue.complete(str(claimed["job_id"]), self._worker_id, result=terminal)
        if completed:
            RunStore(db).update_metadata(
                str(claimed["run_id"]),
                terminal,
                status=str(terminal.get("public_status") or "completed"),
            )
        return completed

    def _record_resume(self, claimed: dict[str, Any]) -> None:
        db = self._database()
        try:
            checkpoint = CheckpointStore(db).load(str(claimed["run_id"])) or {}
            step = str(checkpoint.get("step_id") or checkpoint.get("stage") or "unknown")
            EventStore(db).append(
                TraceEvent(
                    stage="job_resume",
                    status="running",
                    elapsed_ms=0.0,
                    summary="Restarting durable research job from the last persisted checkpoint",
                    run_id=str(claimed["run_id"]),
                    thread_id=str(claimed["run_id"]),
                    metadata={"restarted_from_step": step, "attempt": claimed.get("attempts")},
                )
            )
        finally:
            db.close()

    def _execute(self, run_id: str, query: str, payload: dict[str, Any]) -> None:
        db = self._database()
        queue = JobQueue(db, lease_seconds=self._lease_seconds)
        claimed = queue.get(run_id)
        if claimed is None or claimed.get("status") != "running":
            db.close()
            return
        run_store = RunStore(db)
        event_store = EventStore(db)
        checkpoints = CheckpointStore(db)
        run = run_store.get(run_id) or {}
        job = _job_from_metadata(run_id, dict(run.get("metadata") or {}))
        job.status = "running"
        with self._lock:
            payload.update(self._secrets.get(run_id) or {})
        updates = _model_env_updates(payload)
        output_dir = _path_value(payload.get("output_dir"), "reports/workbench/query")
        mode = str(payload.get("mode") or "phase2")
        depth = str(payload.get("depth") or "standard")
        last_step = run_store.last_step(run_id)
        step_seq = int((last_step or {}).get("seq") or 0)
        trace_count = 0
        last_draft = ""
        last_verified = ""
        heartbeat_stop = threading.Event()

        def heartbeat() -> None:
            while not heartbeat_stop.wait(max(1.0, self._lease_seconds / 3.0)):
                heartbeat_db = self._database()
                try:
                    if not JobQueue(heartbeat_db, lease_seconds=self._lease_seconds).heartbeat(
                        run_id, self._worker_id
                    ):
                        return
                finally:
                    heartbeat_db.close()

        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()

        def persist_job(*, run_status: str | None = None) -> None:
            run_store.update_metadata(
                run_id,
                _job_metadata(job),
                status=run_status or job.status,
            )

        def emit_stage(
            events: list[Any],
            stage: str,
            status: str,
            summary: str,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if job.progress.get(stage) == status:
                return
            trace_event = TraceEvent(
                stage=stage,
                status=status,
                elapsed_ms=round((time.time() - job.started_at) * 1000, 2),
                summary=summary,
                run_id=run_id,
                thread_id=run_id,
                metadata=metadata or {},
            )
            events.append(trace_event)
            job.current_stage = stage
            job.progress[stage] = status

        def should_stop() -> None:
            fresh = queue.get(run_id)
            if fresh is None or fresh.get("status") == "cancelled":
                job.cancel_reason = str(
                    ((run_store.get(run_id) or {}).get("metadata") or {}).get("cancel_reason")
                    or "user"
                )
                job._cancel_flag.set()
            _enforce_job_stop(job, job.started_at)

        def on_state(state: dict[str, Any], events: list[Any]) -> None:
            nonlocal trace_count, last_draft, last_verified, step_seq
            final_answer = str(state.get("final_answer") or "")
            verified_answer = str(state.get("_verified_answer") or "")
            if final_answer and final_answer != last_draft:
                snapshot_stage = "verified" if verified_answer and final_answer == verified_answer else "draft"
                _capture_report_snapshot(job, state, output_dir, stage=snapshot_stage)
                last_draft = final_answer
                if snapshot_stage == "verified":
                    last_verified = verified_answer
            if verified_answer and verified_answer != last_verified:
                _capture_report_snapshot(
                    job,
                    {**state, "final_answer": verified_answer},
                    output_dir,
                    stage="verified",
                )
                last_verified = verified_answer

            pipeline_stage = str(state.get("_pipeline_stage") or "")
            event_mode = str((state.get("_run_summary") or {}).get("mode") or "")
            if event_mode:
                job.pipeline = event_mode
            gap_round = max(
                int(state.get("_gap_iteration") or 0),
                int(state.get("_coverage_iteration") or 0),
            )
            if pipeline_stage in {"synthesized", "dynamically_synthesized"}:
                emit_stage(events, "report_draft", "completed", "报告初稿已生成")
                emit_stage(events, "verification_round", "running", "第一轮核验")
            elif pipeline_stage == "verified_revised":
                emit_stage(events, "verification_round", "completed", "第一轮核验完成")
                emit_stage(events, "final_commit", "running", "最终提交")
            elif pipeline_stage in {"gap_researched", "targeted_gap_researched"}:
                emit_stage(
                    events,
                    "targeted_gap_research",
                    "completed",
                    f"针对性补证第 {max(1, gap_round)} 轮完成",
                    {"round": max(1, gap_round)},
                )
                emit_stage(events, "reanalysis", "running", "重新分析")
            elif pipeline_stage in {"model_analyzed", "generalized_model_analyzed"} and gap_round:
                emit_stage(events, "reanalysis", "completed", "重新分析完成")
            elif pipeline_stage == "completed":
                emit_stage(events, "final_commit", "running", "最终提交")

            for trace_event in events[trace_count:]:
                event_store.append(trace_event)
                job.current_stage = str(getattr(trace_event, "stage", job.current_stage))
                job.progress[job.current_stage] = str(getattr(trace_event, "status", "completed"))
            trace_count = len(events)
            _persist_trace_snapshot(job, events, output_dir)
            job.source_statuses = {
                source: value.get("status") if isinstance(value, dict) else str(value)
                for source, value in (state.get("_source_statuses") or {}).items()
            }
            job.factcheck_status = str(state.get("_factcheck_status") or job.factcheck_status)
            job.delivery_status = str(state.get("_delivery_status") or job.delivery_status)
            job.quality = dict(state.get("_audit_metrics") or job.quality)
            job.artifacts.update(
                {
                    str(key): str(value)
                    for key, value in (state.get("_report_artifacts") or {}).items()
                    if value
                }
            )
            step_seq += 1
            checkpoint = _checkpoint_payload(state, job, step_seq)
            checkpoints.save(run_id, f"{step_seq:06d}", checkpoint)
            run_store.add_step(
                run_id,
                {
                    "status": "completed",
                    "capability_id": "research.query.state",
                    "output": {
                        "stage": checkpoint["stage"],
                        "progress": checkpoint["progress"],
                    },
                },
                step_id=f"{run_id}:{step_seq:06d}",
                seq=step_seq,
            )
            persist_job(run_status="running")
            queue.heartbeat(run_id, self._worker_id)

        try:
            persist_job(run_status="running")
            should_stop()
            context = RunContext(
                run_id=run_id,
                thread_id=run_id,
                workspace=str(config.PROJECT_ROOT),
                config_overrides=updates,
            )
            from conflux.__main__ import query_command

            state = query_command(
                query,
                mode=mode,
                output_dir=output_dir,
                stream_events=False,
                trace_dir=output_dir,
                run_id=run_id,
                depth=depth,
                started_at=job.started_at,
                deadline_at=job.deadline_at,
                commit_reserve_seconds=job.commit_reserve_seconds,
                run_context=context,
                ledger_db_path=self._db_path,
                on_graph_state=on_state,
                should_stop=should_stop,
            )
            _capture_report_snapshot(
                job,
                state,
                output_dir,
                stage="verified" if state.get("_verified_answer") else "draft",
            )
            job.source_statuses = {
                source: value.get("status") if isinstance(value, dict) else str(value)
                for source, value in (state.get("_source_statuses") or {}).items()
            }
            job.factcheck_status = str(state.get("_factcheck_status") or "")
            job.pipeline = str((state.get("_run_summary") or {}).get("mode") or "")
            job.delivery_status = str(state.get("_delivery_status") or "")
            job.quality = dict(state.get("_audit_metrics") or {})
            job.artifacts.update(
                {
                    str(key): str(value)
                    for key, value in (state.get("_report_artifacts") or {}).items()
                    if value
                }
            )
            final_events: list[Any] = []
            emit_stage(final_events, "final_commit", "completed", "最终提交完成")
            for trace_event in final_events:
                event_store.append(trace_event)
            job.warnings.extend(
                warning for warning in _state_warnings(state) if warning not in job.warnings
            )
            if _deadline_exceeded(job):
                job.cancel_reason = "timeout"
                _finish_job(
                    job,
                    "timed_out",
                    "Run completed report commit after the absolute deadline.",
                    preserve_report=True,
                )
            else:
                job.ended_at = time.time()
                if job.delivery_status == "diagnostic_only":
                    job.status = "completed_diagnostic"
                else:
                    job.status = "completed_with_warnings" if job.warnings else "completed"
            result = _job_metadata(job)
            checkpoints.save(
                run_id,
                "final",
                {
                    **_checkpoint_payload(state, job, step_seq + 1),
                    "complete": True,
                    "terminal_result": result,
                },
            )
            if queue.complete(run_id, self._worker_id, result=result):
                persist_job(run_status=job.status)
        except _JobCancelled as exc:
            _finish_job(job, "cancelled", str(exc), preserve_report=True)
            queue.cancel(run_id)
            persist_job(run_status="cancelled")
        except _JobTimedOut as exc:
            _finish_job(job, "timed_out", str(exc), preserve_report=True)
            result = _job_metadata(job)
            queue.complete(run_id, self._worker_id, result=result)
            persist_job(run_status=job.status)
        except SystemExit as exc:
            _finish_job(job, "failed", f"SystemExit code={exc.code}", preserve_report=True)
            queue.fail(run_id, self._worker_id, job.error, retryable=False)
            persist_job(run_status="failed")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            fresh = queue.get(run_id)
            if fresh and fresh.get("status") == "cancelled":
                job.cancel_reason = "user"
            if job.cancel_reason == "user":
                _finish_job(job, "cancelled", error, preserve_report=True)
                queue.cancel(run_id)
                persist_job(run_status="cancelled")
            elif job.cancel_reason == "timeout" or _deadline_exceeded(job):
                job.cancel_reason = "timeout"
                _finish_job(job, "timed_out", error, preserve_report=True)
                result = _job_metadata(job)
                queue.complete(run_id, self._worker_id, result=result)
                persist_job(run_status=job.status)
            else:
                _finish_job(job, "failed", error, preserve_report=True)
                queue.fail(run_id, self._worker_id, job.error, retryable=False)
                persist_job(run_status="failed")
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1.0)
            with self._lock:
                self._secrets.pop(run_id, None)
            db.close()


def _checkpoint_payload(state: dict[str, Any], job: ResearchJob, step_id: int) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "stage": str(state.get("_pipeline_stage") or job.current_stage or "running"),
        "progress": dict(job.progress),
        "final_answer": str(state.get("final_answer") or ""),
        "verified_answer": str(state.get("_verified_answer") or ""),
        "source_statuses": state.get("_source_statuses") or {},
        "run_summary": state.get("_run_summary") or {},
        "report_artifacts": state.get("_report_artifacts") or {},
        "delivery_status": str(state.get("_delivery_status") or ""),
        "audit_metrics": state.get("_audit_metrics") or {},
        "complete": False,
    }


def _path_value(value: Any, default: str) -> str:
    text = str(value or default).strip()
    path = Path(text).expanduser()
    if path.is_absolute():
        return str(path)
    return str(config.PROJECT_ROOT / path)


def _model_env_updates(payload: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    base_url = str(payload.get("base_url") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    embedding_base_url = str(payload.get("embedding_base_url") or "").strip()
    embedding_api_key = str(payload.get("embedding_api_key") or "").strip()
    embedding_model = str(payload.get("embedding_model") or "").strip()

    depth = str(payload.get("depth") or "standard").strip().lower()
    if depth not in {"quick", "standard", "deep"}:
        depth = "standard"
    preset = depth.upper()
    model_override = bool(base_url or api_key or model)
    if model_override:
        updates[f"CONFLUX_MODELS__{preset}__PROVIDER"] = "openai_compatible"
        if base_url:
            updates[f"CONFLUX_MODELS__{preset}__BASE_URL"] = base_url
        if api_key:
            updates[f"CONFLUX_MODELS__{preset}__API_KEY"] = api_key
        if model:
            updates[f"CONFLUX_MODELS__{preset}__MODEL"] = model
        for role in ("PLANNER", "ANALYST", "RERANKER", "SYNTHESIZER", "VERIFIER"):
            updates[f"CONFLUX_RESEARCH__PROFILES__{preset}__{role}_MODEL"] = depth
    if embedding_base_url or base_url:
        updates["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url or base_url
    if embedding_api_key or api_key:
        updates["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key or api_key
    if embedding_model:
        updates["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    updates["CONFLUX_RESEARCH__DEPTH"] = depth
    if depth == "quick":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "1"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "false"
        updates["CONFLUX_RETRIEVAL__TOP_K"] = "3"
        updates["CONFLUX_RETRIEVAL__FINAL_K"] = "3"
    elif depth == "deep":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "5"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "true"
        updates["CONFLUX_RESEARCH__MAX_DEEP_QUESTIONS"] = "5"
    return updates


_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
