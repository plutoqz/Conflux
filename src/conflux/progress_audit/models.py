"""Stable contracts for project snapshots and progress audit reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


TestStatus = Literal["not_run", "passed", "failed", "timed_out", "error"]


@dataclass(slots=True)
class GitCommit:
    sha: str
    subject: str
    committed_at: str = ""


@dataclass(slots=True)
class ArtifactRecord:
    path: str
    category: str
    size_bytes: int
    modified_at: str
    fingerprint: str


@dataclass(slots=True)
class TestResult:
    status: TestStatus = "not_run"
    command: str = ""
    exit_code: int | None = None
    elapsed_ms: int = 0
    output: str = ""


@dataclass(slots=True)
class ProjectSnapshot:
    project_id: str
    path: str
    captured_at: datetime
    git_available: bool = False
    git_root: str = ""
    git_branch: str = ""
    git_head: str = ""
    dirty_files: list[str] = field(default_factory=list)
    recent_commits: list[GitCommit] = field(default_factory=list)
    test_result: TestResult = field(default_factory=TestResult)
    result_files: list[ArtifactRecord] = field(default_factory=list)
    report_files: list[ArtifactRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["captured_at"] = self.captured_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectSnapshot":
        captured_at = _parse_datetime(payload.get("captured_at"))
        return cls(
            project_id=str(payload.get("project_id") or ""),
            path=str(payload.get("path") or ""),
            captured_at=captured_at,
            git_available=bool(payload.get("git_available", bool(payload.get("git_head")))),
            git_root=str(payload.get("git_root") or ""),
            git_branch=str(payload.get("git_branch") or ""),
            git_head=str(payload.get("git_head") or ""),
            dirty_files=[str(item) for item in payload.get("dirty_files") or []],
            recent_commits=[GitCommit(**item) for item in payload.get("recent_commits") or []],
            test_result=TestResult(**(payload.get("test_result") or {})),
            result_files=[ArtifactRecord(**item) for item in payload.get("result_files") or []],
            report_files=[ArtifactRecord(**item) for item in payload.get("report_files") or []],
            errors=[str(item) for item in payload.get("errors") or []],
        )


@dataclass(slots=True)
class ProgressClaim:
    summary: str
    evidence_refs: list[str]

    def __post_init__(self) -> None:
        self.evidence_refs = [str(ref).strip() for ref in self.evidence_refs if str(ref).strip()]
        if not self.evidence_refs:
            raise ValueError("A real progress claim requires at least one evidence reference")


@dataclass(slots=True)
class ProgressAuditReport:
    project_id: str
    period: str
    captured_at: datetime
    baseline_status: str
    real_progress: list[ProgressClaim] = field(default_factory=list)
    weak_signals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    snapshot: ProjectSnapshot | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["captured_at"] = self.captured_at.isoformat()
        payload["snapshot"] = self.snapshot.to_dict() if self.snapshot else None
        return payload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return utc_now()
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
