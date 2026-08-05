"""Async job manager for Conflux research queries.

Provides background execution with SSE-streamable trace events, status
polling, and best-effort cancellation.  Designed to replace the blocking
``POST /api/query/run`` with an async lifecycle:

    POST /api/query/jobs           -> 202 { run_id, events_url }
    GET  /api/query/jobs/{id}      -> current status + final result
    GET  /api/query/jobs/{id}/events -> SSE stream of TraceEvent dicts
    POST /api/query/jobs/{id}/cancel -> best-effort cancel
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conflux import config
from conflux.trace import new_run_id

# Serialize graph execution to prevent concurrent monkey-patching
# and global env/stdout corruption between jobs.
_EXECUTION_LOCK = threading.RLock()


class _JobCancelled(RuntimeError):
    pass


class _JobTimedOut(RuntimeError):
    pass


# ── Append-only event log (multi-consumer safe) ────────────


class _EventLog:
    """Thread-safe append-only event log with per-consumer cursors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict | None] = []  # None = sentinel
        self._closed = False
        self._notify = threading.Condition(self._lock)

    def append(self, event: dict | None) -> int:
        """Append an event, return its 0-based index."""
        with self._lock:
            if self._closed:
                return -1
            self._events.append(event)
            if event is None:
                self._closed = True
            self._notify.notify_all()
            return len(self._events) - 1

    def read_from(self, cursor: int, timeout: float = 30.0) -> tuple[list[dict | None], int, bool]:
        """Block up to *timeout* seconds for new events after *cursor*.

        Returns (events_since_cursor, next_cursor, closed).
        """
        with self._lock:
            while cursor >= len(self._events) and not self._closed:
                if not self._notify.wait(timeout):
                    break
            if cursor >= len(self._events):
                return [], cursor, self._closed
            batch = self._events[cursor:]
            return batch, len(self._events), self._closed


# ── Job model ──────────────────────────────────────────────


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
    formal_delivery = True
    has_report = bool(
        preserve_report
        and formal_delivery
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
    """Compatibility wrapper; completed report data is intentionally preserved."""

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


# ── JobManager ─────────────────────────────────────────────


class JobManager:
    """Singleton registry of in-flight and recent research jobs.

    Expires terminal jobs after *ttl_seconds*.
    """

    MAX_JOBS = 100

    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, ResearchJob] = {}
        self._ttl = ttl_seconds
        self._cleaner_started = False

    def submit(self, query: str, payload: dict[str, Any], *, run_id: str | None = None) -> dict[str, Any]:
        """Create a new job and start it in a background thread."""
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
        )
        with self._lock:
            if len(self._jobs) >= self.MAX_JOBS:
                raise RuntimeError(f"Job limit reached ({self.MAX_JOBS}). Wait for older jobs to expire.")
            self._jobs[run_id] = job
            self._maybe_start_cleaner()

        job.thread = threading.Thread(
            target=self._execute, args=(run_id, query, payload), daemon=True
        )
        job.thread.start()

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
        """Return the current status dict for a job, or None."""
        job = self._jobs.get(run_id)
        if job is None:
            return None
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

    def event_log(self, run_id: str) -> _EventLog | None:
        """Return the append-only event log for SSE streaming."""
        job = self._jobs.get(run_id)
        return job._event_log if job else None

    def cancel(self, run_id: str, *, reason: str = "user") -> bool:
        """Signal a best-effort cancel for an active job."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None or not job.active:
                return False
            job.cancel_reason = "timeout" if reason == "timeout" else "user"
            job._cancel_flag.set()
            return True

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent jobs, newest first."""
        with self._lock:
            sorted_jobs = sorted(
                self._jobs.values(), key=lambda j: j.started_at, reverse=True
            )
        return [
            {
                "run_id": j.run_id,
                "query": j.query[:200],
                "status": j.status,
                "started_at": j.started_at,
                "ended_at": j.ended_at,
            }
            for j in sorted_jobs[:limit]
        ]

    # ── Internal ───────────────────────────────────────────

    def _execute(self, run_id: str, query: str, payload: dict[str, Any]) -> None:
        """Background execution of the Conflux query pipeline."""
        job = self._jobs.get(run_id)
        if job is None:
            return
        updates = _model_env_updates(payload)
        output_dir = _path_value(payload.get("output_dir"), "reports/workbench/query")
        mode = str(payload.get("mode") or "phase2")
        depth = str(payload.get("depth") or "standard")

        stream = io.StringIO()
        live_events: list[Any] = []
        try:
            with _EXECUTION_LOCK:
                # Include time spent waiting for the execution lock in the tier deadline.
                _enforce_job_stop(job, job.started_at)
                job.status = "running"

                with _temporary_env(updates), contextlib.redirect_stdout(stream):
                    from conflux.__main__ import query_command
                    from conflux.trace import TraceEvent, event_from_state_key

                    # ── Patch _run_phase2_graph for real-time events ──
                    import conflux.__main__ as main_mod
                    _original_run_phase2 = main_mod._run_phase2_graph

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
                        job._event_log.append(trace_event.to_dict())

                    def _instrumented_run_phase2(graph, initial_state, query2, *, stream_events=False, thread_id=None):
                        started_at_ts = job.started_at
                        event = initial_state
                        seen = set()
                        events = live_events
                        last_draft = ""
                        last_verified = ""
                        config_graph = main_mod.graph_config(thread_id)
                        for event in graph.stream(initial_state, config=config_graph, stream_mode="values"):
                            final_answer = str(event.get("final_answer") or "")
                            verified_answer = str(event.get("_verified_answer") or "")
                            if final_answer and final_answer != last_draft:
                                snapshot_stage = (
                                    "verified"
                                    if verified_answer and final_answer == verified_answer
                                    else "draft"
                                )
                                _capture_report_snapshot(
                                    job, event, output_dir, stage=snapshot_stage
                                )
                                last_draft = final_answer
                                if snapshot_stage == "verified":
                                    last_verified = verified_answer
                            if verified_answer and verified_answer != last_verified:
                                _capture_report_snapshot(
                                    job,
                                    {**event, "final_answer": verified_answer},
                                    output_dir,
                                    stage="verified",
                                )
                                last_verified = verified_answer

                            pipeline_stage = str(event.get("_pipeline_stage") or "")
                            event_mode = str((event.get("_run_summary") or {}).get("mode") or "")
                            if event_mode:
                                job.pipeline = event_mode
                            gap_round = max(
                                int(event.get("_gap_iteration") or 0),
                                int(event.get("_coverage_iteration") or 0),
                            )
                            if pipeline_stage in {"synthesized", "dynamically_synthesized"}:
                                emit_stage(events, "report_draft", "completed", "报告初稿已生成")
                                emit_stage(events, "verification_round", "running", "第一轮核验")
                            elif pipeline_stage == "verified_revised":
                                emit_stage(events, "verification_round", "completed", "第一轮核验完成")
                                statuses = event.get("_source_statuses") or {}
                                external_available = any(
                                    str((statuses.get(source) or {}).get("status") or "")
                                    in {"success", "low_relevance"}
                                    for source in ("RAG", "Web")
                                )
                                if (
                                    event.get("_gap_questions")
                                    and external_available
                                    and job.deadline_at - time.time() >= 90
                                ):
                                    emit_stage(
                                        events,
                                        "targeted_gap_research",
                                        "running",
                                        f"针对性补证 · 第 {gap_round + 1} 轮",
                                        {"round": gap_round + 1},
                                    )
                                else:
                                    emit_stage(events, "final_commit", "running", "最终提交")
                            elif pipeline_stage in {"gap_researched", "targeted_gap_researched"}:
                                emit_stage(
                                    events,
                                    "targeted_gap_research",
                                    "completed",
                                    f"针对性补证 · 第 {max(1, gap_round)} 轮完成",
                                    {"round": max(1, gap_round)},
                                )
                                emit_stage(events, "reanalysis", "running", "重新分析")
                            elif pipeline_stage in {"model_analyzed", "generalized_model_analyzed"} and gap_round:
                                emit_stage(events, "reanalysis", "completed", "重新分析完成")
                            elif pipeline_stage == "completed":
                                emit_stage(events, "final_commit", "running", "最终提交")

                            for key, label in [
                                ("_research_plan", "Research Plan"),
                                ("_domain_map", "Domain Map"),
                                ("rag_result", "RAG Agent"),
                                ("web_result", "Web Agent"),
                                ("model_result", "Model Agent"),
                                ("_merged", "Evidence Merge"),
                                ("_coverage_matrix", "Coverage Review"),
                                ("_section_contracts", "Section Contracts"),
                                ("_section_drafts", "Section Synthesis"),
                                ("_arbitration", "Arbitration"),
                                ("final_answer", "Synthesis"),
                                ("_verified_answer", "FactCheck"),
                                ("_factcheck_report", "Verify & Revise"),
                                ("_verification_issues", "Verify & Revise"),
                                ("_deep_queries", "Gap Research"),
                                ("_deep_research", "L4 Deep Research"),
                            ]:
                                value = event.get(key)
                                if value and key not in seen:
                                    seen.add(key)
                                    trace_event = event_from_state_key(
                                        key, value,
                                        run_id=run_id, thread_id=thread_id,
                                        started_at=started_at_ts,
                                    )
                                    if trace_event:
                                        if key == "final_answer" and event.get("_synthesis_status"):
                                            trace_event.status = str(event["_synthesis_status"])
                                            trace_event.metadata["synthesis_error"] = str(
                                                event.get("_synthesis_error") or ""
                                            )
                                        events.append(trace_event)
                                        job.current_stage = trace_event.stage
                                        job.progress[trace_event.stage] = trace_event.status
                                        job._event_log.append(trace_event.to_dict())
                            _persist_trace_snapshot(job, events, output_dir)
                            _enforce_job_stop(job, started_at_ts)
                        return event, events

                    main_mod._run_phase2_graph = _instrumented_run_phase2
                    try:
                        state = query_command(
                            query, mode=mode, output_dir=output_dir,
                            stream_events=False, trace_dir=output_dir,
                            run_id=run_id,
                            depth=depth,
                            started_at=job.started_at,
                            deadline_at=job.deadline_at,
                            commit_reserve_seconds=job.commit_reserve_seconds,
                        )
                    finally:
                        main_mod._run_phase2_graph = _original_run_phase2

            _capture_report_snapshot(
                job,
                state,
                output_dir,
                stage="verified" if state.get("_verified_answer") else "draft",
            )
            job.source_statuses = {
                source: p.get("status") if isinstance(p, dict) else str(p)
                for source, p in (state.get("_source_statuses") or {}).items()
            }
            job.factcheck_status = str(state.get("_factcheck_status") or "")
            job.pipeline = str((state.get("_run_summary") or {}).get("mode") or "")
            job.delivery_status = str(state.get("_delivery_status") or "")
            job.quality = dict(state.get("_audit_metrics") or {})
            job.artifacts.update({
                str(key): str(value)
                for key, value in (state.get("_report_artifacts") or {}).items()
                if value
            })

            emit_stage(live_events, "final_commit", "completed", "最终提交完成")
            _persist_trace_snapshot(job, live_events, output_dir)
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
        except _JobCancelled as exc:
            _finish_job(job, "cancelled", str(exc), preserve_report=True)
        except _JobTimedOut as exc:
            _finish_job(job, "timed_out", str(exc), preserve_report=True)
        except SystemExit as exc:
            error = f"SystemExit code={exc.code}: {stream.getvalue()[-500:]}"
            if job.cancel_reason == "timeout" or _deadline_exceeded(job):
                job.cancel_reason = "timeout"
                _finish_job(job, "timed_out", error, preserve_report=True)
            else:
                _finish_job(job, "failed", error, preserve_report=True)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            if job.cancel_reason == "timeout" or _deadline_exceeded(job):
                job.cancel_reason = "timeout"
                _finish_job(job, "timed_out", error, preserve_report=True)
            elif job.cancel_reason == "user":
                _finish_job(job, "cancelled", error, preserve_report=True)
            else:
                _finish_job(job, "failed", error, preserve_report=True)

        job._event_log.append(None)  # sentinel

    def _maybe_start_cleaner(self) -> None:
        if self._cleaner_started:
            return
        self._cleaner_started = True

        def _clean():
            while True:
                time.sleep(600)
                with self._lock:
                    now = time.time()
                    stale = [
                        rid for rid, j in self._jobs.items()
                        if not j.active and j.ended_at and (now - j.ended_at) > self._ttl
                    ]
                    for rid in stale:
                        del self._jobs[rid]

        threading.Thread(target=_clean, daemon=True).start()


# ── Helpers ────────────────────────────────────────────────


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
        updates["CONFLUX_RETRIEVAL__TOP_K"] = "15"
        updates["CONFLUX_RETRIEVAL__FINAL_K"] = "10"
    return updates


@contextlib.contextmanager
def _temporary_env(updates: dict[str, str]):
    old_values = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value:
                os.environ[key] = value
        config._config = None
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config._config = None


# Singleton
_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
