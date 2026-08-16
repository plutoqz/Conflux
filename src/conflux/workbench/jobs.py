"""Durable Workbench research-query jobs backed by the M3 SQLite stores."""

from __future__ import annotations

import hashlib
import json
import os
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


class IdempotencyConflict(RuntimeError):
    """Same idempotency key submitted with a different semantic request."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(f"idempotency conflict for key {idempotency_key!r}")
        self.idempotency_key = idempotency_key


def _request_hash(query: str, payload: dict[str, Any]) -> str:
    """Stable semantic hash of a submit request (secrets excluded)."""
    semantic = {
        "query": str(query or "").strip(),
        "payload": _sanitize_payload(dict(payload)),
    }
    return hashlib.sha256(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _wait_estimate(queue: Any, run_id: str, own_timeout_seconds: float) -> dict[str, int]:
    """Coarse wait range until run_id starts: 0 to remaining budgets ahead plus own timeout."""
    now = time.time()
    ahead_seconds = 0.0
    for item in queue.list(kind=RESEARCH_JOB_KIND, status="pending", limit=1000):
        if str(item.get("job_id") or "") == run_id:
            break
        payload = item.get("payload") or {}
        try:
            started = float(payload.get("started_at") or 0.0)
            timeout = float(payload.get("timeout_seconds") or 300.0)
        except (TypeError, ValueError):
            started, timeout = 0.0, 300.0
        ahead_seconds += max(0.0, started + timeout - now) if started else timeout
    return {
        "min_seconds": 0,
        "max_seconds": int(round(ahead_seconds + max(0.0, own_timeout_seconds))),
    }


# ---------------------------------------------------------------------------
# P1.3 运行冻结（run manifest）：提交时固定 revision/模型/预算/凭证来源，
# 重启后按同一冻结恢复，凭证不可解析或配置漂移时 fail-closed。
# ---------------------------------------------------------------------------

def _git_head_revision() -> str:
    """Current git HEAD revision (40-hex) or '' when unavailable."""
    git_dir = Path(config.PROJECT_ROOT) / ".git"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        try:
            return (git_dir / ref).read_text(encoding="utf-8").strip()[:40]
        except OSError:
            try:
                for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
                    if line.endswith(f" {ref}"):
                        return line.split(" ", 1)[0][:40]
            except OSError:
                return ""
            return ""
    return head[:40]


def _model_roles_for(depth: str, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Resolved (provider, model) identity per research role for the frozen manifest."""
    base_url = str(payload.get("base_url") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    if base_url or api_key or model:
        return {
            role: {
                "preset": str(depth),
                "provider": "openai_compatible",
                "model": model,
                "base_url": base_url,
            }
            for role in ("planner", "analyst", "reranker", "synthesizer", "verifier")
        }
    from conflux.research_modes import research_model_diagnostics

    try:
        resolved = research_model_diagnostics(depth)
    except Exception:
        return {}
    roles: dict[str, dict[str, str]] = {}
    for role, cfg in (resolved.get("roles") or {}).items():
        roles[str(role)] = {
            "preset": str(cfg.get("preset") or ""),
            "provider": str(cfg.get("provider") or ""),
            "model": str(cfg.get("model") or ""),
            "base_url": str(cfg.get("base_url") or ""),
        }
    return roles


def _embedding_identity(payload: dict[str, Any]) -> dict[str, str]:
    base_url = str(payload.get("embedding_base_url") or payload.get("base_url") or "").strip()
    model = str(payload.get("embedding_model") or "").strip()
    if not base_url:
        base_url = str(config.get("embedding", "base_url", default="") or "")
    if not model:
        model = str(config.get("embedding", "model", default="") or "")
    return {
        "provider": str(config.get("embedding", "provider", default="") or ""),
        "model": model,
        "base_url": base_url,
    }


def _panel_model_identities(profile: Any) -> dict[str, dict[str, str]]:
    identities: dict[str, dict[str, str]] = {}
    if profile is None or not getattr(profile, "panel_enabled", False):
        return identities
    presets: list[str] = []
    for members in (getattr(profile, "panel_roster", {}) or {}).values():
        presets.extend(str(member) for member in (members or []))
    referee = str(getattr(profile, "panel_referee", "") or "")
    if referee:
        presets.append(referee)
    for preset in dict.fromkeys(presets):
        cfg = config.get("models", preset, default={}) or {}
        if isinstance(cfg, dict):
            identities[str(preset)] = {
                "provider": str(cfg.get("provider") or ""),
                "model": str(cfg.get("model") or ""),
            }
    return identities


def _prompt_source_hash() -> str:
    prompt_file = Path(config.PROJECT_ROOT) / "src" / "conflux" / "research_prompts.py"
    try:
        text = prompt_file.read_text(encoding="utf-8")
    except OSError:
        return "unavailable"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _freeze_inputs(depth: str, effective_payload: dict[str, Any]) -> dict[str, Any]:
    """Deterministic snapshot of execution-relevant inputs (never includes key values)."""
    from conflux.research_modes import resolve_research_profile

    try:
        profile = resolve_research_profile(depth)
    except Exception:
        profile = None
    roles = _model_roles_for(depth, effective_payload)
    embedding = _embedding_identity(effective_payload)
    panel_models = _panel_model_identities(profile)
    semantic = {
        "depth": str(depth),
        "roles": roles,
        "embedding": embedding,
        "panel_models": panel_models,
        "prompt_hash": _prompt_source_hash(),
        "budget": {
            "timeout_seconds": int(getattr(profile, "timeout_seconds", 0) or 0),
            "commit_reserve_seconds": int(getattr(profile, "commit_reserve_seconds", 0) or 0),
            "token_budget": int(getattr(profile, "token_budget", 0) or 0),
            "model_timeout_seconds": int(getattr(profile, "model_timeout_seconds", 0) or 0),
            "max_retries": int(getattr(profile, "max_retries", 0) or 0),
        },
        "panel": (
            {
                "enabled": bool(getattr(profile, "panel_enabled", False)),
                "roster": dict(getattr(profile, "panel_roster", {}) or {}),
                "referee": str(getattr(profile, "panel_referee", "") or ""),
            }
            if profile is not None
            else {}
        ),
    }
    return {
        **semantic,
        "semantic_hash": hashlib.sha256(
            json.dumps(semantic, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
    }


def _credential_refs(
    depth: str,
    effective_payload: dict[str, Any],
    roles: dict[str, dict[str, str]],
    panel_presets: list[str],
) -> list[dict[str, str]]:
    """Stable credential references for the run — names only, never values."""
    refs: list[dict[str, str]] = []

    def add(ref: str, policy: str, scope: str) -> None:
        if not ref or any(item["ref"] == ref for item in refs):
            return
        refs.append({"ref": ref, "policy": policy, "scope": scope})

    payload_keys = {
        key: value
        for key, value in effective_payload.items()
        if key.casefold() in _SECRET_FIELDS or key.casefold().endswith("_api_key")
    }
    if payload_keys.get("api_key"):
        add("workbench_payload:api_key", "fail_closed", f"models.{depth}.api_key")
    else:
        presets = {str(role.get("preset") or "") for role in roles.values()}
        presets.update(str(preset) for preset in panel_presets)
        presets.discard("")
        for preset in sorted(presets):
            env_var = f"CONFLUX_MODELS__{preset.upper()}__API_KEY"
            if os.environ.get(env_var):
                add(f"env:{env_var}", "resume", f"models.{preset}.api_key")
            elif config.get("models", preset, "api_key", default=None):
                add(f"config:models.{preset}.api_key", "resume", f"models.{preset}.api_key")
    if payload_keys.get("embedding_api_key"):
        add("workbench_payload:embedding_api_key", "fail_closed", "embedding.api_key")
    else:
        env_var = "CONFLUX_EMBEDDING__API_KEY"
        if os.environ.get(env_var):
            add(f"env:{env_var}", "resume", "embedding.api_key")
        elif config.get("embedding", "api_key", default=None):
            add("config:embedding.api_key", "resume", "embedding.api_key")
    return refs


def _resolve_credential(ref: str, available_secrets: dict[str, Any]) -> Any:
    if ref.startswith("workbench_payload:"):
        return (available_secrets or {}).get(ref.split(":", 1)[1])
    if ref.startswith("env:"):
        return os.environ.get(ref.split(":", 1)[1])
    if ref.startswith("config:"):
        return config.get(*ref.split(":", 1)[1].split("."), default=None)
    return None


def _verify_frozen(
    manifest: dict[str, Any],
    depth: str,
    effective_payload: dict[str, Any],
    available_secrets: dict[str, Any],
) -> str | None:
    """Return an error string when the run cannot be restored on its frozen inputs.

    Credentials are checked before the semantic hash: a missing temporary key must
    surface as `credential_unavailable_after_restart`, not as a model-identity diff.
    """
    for credential in manifest.get("credentials") or []:
        ref = str((credential or {}).get("ref") or "")
        policy = str((credential or {}).get("policy") or "resume")
        if not ref:
            continue
        if not _resolve_credential(ref, available_secrets):
            if policy == "fail_closed":
                return (
                    "credential_unavailable_after_restart: "
                    f"临时请求凭证引用 {ref} 在重启后不可用；按 fail_closed 终止，"
                    "不静默改用共享环境密钥或其他 Provider。"
                )
            return (
                "credential_unavailable_after_restart: "
                f"凭证引用 {ref} 当前不可解析；拒绝在凭证配置变化后恢复运行。"
            )
    try:
        current = _freeze_inputs(depth, effective_payload)
    except Exception as exc:
        return f"frozen_config_verification_error: {type(exc).__name__}: {exc}"
    if str(current.get("semantic_hash") or "") != str(manifest.get("semantic_hash") or ""):
        return (
            "frozen_config_mismatch: provider/model/Prompt/预算解析与提交时冻结不一致；"
            "拒绝用漂移配置恢复运行。"
        )
    return None


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
    run_manifest: dict[str, Any] = field(default_factory=dict)
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


def _write_failure_diagnostic(
    job: ResearchJob,
    output_dir: str,
    *,
    status: str,
    error: str,
    retryable: bool,
) -> None:
    """Persist a user-readable failure artifact without treating it as a report."""

    diagnostic = {
        "schema_version": "conflux.research_failure.v1",
        "run_id": job.run_id,
        "query": job.query,
        "status": status,
        "error_type": str(error).partition(":")[0],
        "error": str(error),
        "occurred_at": time.time(),
        "current_stage": job.current_stage,
        "progress": dict(job.progress),
        "source_statuses": dict(job.source_statuses),
        "formal_report_preserved": bool(
            job.has_report or job.final_answer or job.artifacts.get("markdown_path")
        ),
        "recovery": {
            "retryable": bool(retryable),
            "action": (
                "Retry the run after checking the failed stage and external dependencies."
                if retryable
                else "Fix the recorded contract or configuration error before submitting a new run."
            ),
        },
    }
    root = Path(output_dir)
    json_path = root / f"{job.run_id}.diagnostic.json"
    markdown_path = root / f"{job.run_id}.diagnostic.md"
    markdown = "\n".join(
        [
            "# Conflux research failure diagnostic",
            "",
            f"- Run ID: `{job.run_id}`",
            f"- Status: `{status}`",
            f"- Failed stage: `{job.current_stage or 'unknown'}`",
            f"- Retryable: `{'yes' if retryable else 'no'}`",
            f"- Formal report preserved: `{'yes' if diagnostic['formal_report_preserved'] else 'no'}`",
            "",
            "## Query",
            "",
            job.query,
            "",
            "## Error",
            "",
            f"`{error}`",
            "",
            "## Recovery",
            "",
            str(diagnostic["recovery"]["action"]),
            "",
        ]
    )
    try:
        root.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(markdown, encoding="utf-8")
    except Exception as exc:
        job.warnings.append(
            f"failure diagnostic snapshot failed: {type(exc).__name__}: {exc}"
        )
        return
    job.artifacts["diagnostic_json_path"] = str(json_path.resolve())
    job.artifacts["diagnostic_markdown_path"] = str(markdown_path.resolve())


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
        "run_manifest": dict(job.run_manifest),
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
        run_manifest=dict(metadata.get("run_manifest") or {}),
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

    def submit(
        self,
        query: str,
        payload: dict[str, Any],
        *,
        run_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        run_id = run_id or new_run_id()
        request_hash = _request_hash(query, payload)
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
        # P1.3 运行冻结：把本 run 的模型/预算/凭证来源固定为 manifest（只存引用，不存密钥值）。
        effective_payload = dict(payload)
        effective_payload.update(secrets)
        freeze = _freeze_inputs(depth, effective_payload)
        panel_presets = [str(preset) for preset in (freeze.get("panel_models") or {})]
        job.run_manifest = {
            "schema": "conflux.run_manifest.v1",
            "code_revision": _git_head_revision(),
            "semantic_hash": str(freeze.get("semantic_hash") or ""),
            "depth": str(depth),
            "model_role": str(depth).upper(),
            "roles": dict(freeze.get("roles") or {}),
            "embedding": dict(freeze.get("embedding") or {}),
            "panel_models": dict(freeze.get("panel_models") or {}),
            "prompt_hash": str(freeze.get("prompt_hash") or ""),
            "budget": dict(freeze.get("budget") or {}),
            "credentials": _credential_refs(
                depth,
                effective_payload,
                dict(freeze.get("roles") or {}),
                panel_presets,
            ),
            "model_revision": None,
            "model_revision_verified": False,
            "model_revision_unverified": True,
            "captured_at": started_at,
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
            # The job row and its RunStore row are created in one transaction: the
            # idempotency_key UNIQUE constraint is the concurrency gate, so N duplicate
            # submits race to exactly one job + one run.
            row = queue.enqueue(
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
                request_hash=request_hash,
                idempotency_key=idempotency_key,
                run={
                    "run_id": run_id,
                    "workspace": str(config.PROJECT_ROOT),
                    "status": "pending",
                    "thread_id": run_id,
                    "metadata": _job_metadata(job),
                },
            )
            if idempotency_key and str(row.get("job_id") or "") != run_id:
                # Our insert lost the unique-key race: this is a replay of an earlier
                # submit. Same semantic hash -> return the original run; different
                # request -> surface a 409 conflict to the caller.
                prev_hash = str(row.get("request_hash") or "")
                if prev_hash and prev_hash != request_hash:
                    raise IdempotencyConflict(idempotency_key)
                existing_run_id = str(row.get("run_id") or row.get("job_id") or run_id)
                return {
                    "run_id": existing_run_id,
                    "status": str(row.get("status") or ""),
                    "queue_position": self.queue_position(existing_run_id),
                    "active_count": self.active_count(),
                    "idempotent_replay": True,
                    "wait_estimate": _wait_estimate(queue, existing_run_id, timeout_seconds),
                    "events_url": f"/api/query/jobs/{existing_run_id}/events",
                    "status_url": f"/api/query/jobs/{existing_run_id}",
                }
            wait_estimate = _wait_estimate(queue, run_id, timeout_seconds)
            queue_position = self.queue_position(run_id)
            active_count = self.active_count()
        finally:
            db.close()
        if secrets:
            with self._lock:
                self._secrets[run_id] = secrets
        self._wake.set()
        return {
            "run_id": run_id,
            "status": "pending",
            "queue_position": queue_position,
            "active_count": active_count,
            "wait_estimate": wait_estimate,
            "events_url": f"/api/query/jobs/{run_id}/events",
            "status_url": f"/api/query/jobs/{run_id}",
            "timeout_seconds": job.timeout_seconds,
            "deadline_at": job.deadline_at,
            "commit_reserve_seconds": job.commit_reserve_seconds,
            "request_hash": request_hash,
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

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        """Return the previously submitted job row for a key (or None)."""
        db = self._database()
        try:
            queue = JobQueue(db, lease_seconds=self._lease_seconds)
            return queue.get_by_idempotency_key(idempotency_key)
        finally:
            db.close()

    def queue_position(self, run_id: str) -> int | None:
        """0-based position among pending jobs ahead of (or at) run_id."""
        db = self._database()
        try:
            rows = JobQueue(db, lease_seconds=self._lease_seconds).list(
                kind=RESEARCH_JOB_KIND, status="pending", limit=self.MAX_JOBS + 1
            )
        finally:
            db.close()
        for idx, item in enumerate(rows):
            if str(item.get("job_id")) == run_id:
                return idx
        return None

    def active_count(self) -> int:
        db = self._database()
        try:
            return sum(
                1
                for item in JobQueue(db, lease_seconds=self._lease_seconds).list(
                    kind=RESEARCH_JOB_KIND, limit=self.MAX_JOBS + 1
                )
                if item["status"] in {"pending", "running"}
            )
        finally:
            db.close()

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
        # P1.3 运行冻结验证：凭证先于配置哈希检查（缺失临时密钥必须先报凭证诊断）。
        frozen = dict((run.get("metadata") or {}).get("run_manifest") or {})
        if frozen:
            verdict = _verify_frozen(
                frozen,
                depth,
                payload,
                dict(self._secrets.get(run_id) or {}),
            )
            if verdict:
                job.current_stage = "credential_recovery"
                event_store.append(
                    TraceEvent(
                        stage="credential_recovery",
                        status="failed",
                        elapsed_ms=round((time.time() - job.started_at) * 1000, 2),
                        summary=verdict,
                        run_id=run_id,
                        thread_id=run_id,
                        metadata={
                            "error_code": (
                                "credential_unavailable_after_restart"
                                if "credential_unavailable_after_restart" in verdict
                                else "frozen_config_mismatch"
                            )
                        },
                    )
                )
                _write_failure_diagnostic(
                    job,
                    output_dir,
                    status="failed",
                    error=verdict,
                    retryable=False,
                )
                _finish_job(job, "failed", verdict, preserve_report=False)
                queue.fail(
                    run_id,
                    self._worker_id,
                    verdict,
                    retryable=False,
                    result=_job_metadata(job),
                )
                run_store.update_metadata(run_id, _job_metadata(job), status="failed")
                db.close()
                return
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
            _write_failure_diagnostic(
                job,
                output_dir,
                status="timed_out",
                error=f"{type(exc).__name__}: {exc}",
                retryable=True,
            )
            _finish_job(job, "timed_out", str(exc), preserve_report=True)
            result = _job_metadata(job)
            queue.complete(run_id, self._worker_id, result=result)
            persist_job(run_status=job.status)
        except SystemExit as exc:
            error = f"SystemExit code={exc.code}"
            _write_failure_diagnostic(
                job,
                output_dir,
                status="failed",
                error=error,
                retryable=False,
            )
            _finish_job(job, "failed", error, preserve_report=True)
            queue.fail(
                run_id,
                self._worker_id,
                job.error,
                retryable=False,
                result=_job_metadata(job),
            )
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
                _write_failure_diagnostic(
                    job,
                    output_dir,
                    status="timed_out",
                    error=error,
                    retryable=True,
                )
                _finish_job(job, "timed_out", error, preserve_report=True)
                result = _job_metadata(job)
                queue.complete(run_id, self._worker_id, result=result)
                persist_job(run_status=job.status)
            else:
                _write_failure_diagnostic(
                    job,
                    output_dir,
                    status="failed",
                    error=error,
                    retryable=False,
                )
                _finish_job(job, "failed", error, preserve_report=True)
                queue.fail(
                    run_id,
                    self._worker_id,
                    job.error,
                    retryable=False,
                    result=_job_metadata(job),
                )
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
