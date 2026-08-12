"""P3 project intelligence — core protocol contracts (P3.0 frozen).

Defines the stable JSON schemas for ProjectDocument, ResearchWorkItem,
ProjectContextSnapshot, ProjectEvent, and ReviewItem.  These are the
versioned wire formats for the project state layer; SQLite repositories
serialize them into JSON columns so contracts can evolve without schema
churn (same approach as M3 runtime state).
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# P3 protocol version — bump on breaking contract changes.
P3_PROTOCOL_VERSION: str = "conflux.dev/p3/v1alpha1"


class DocumentKind(str, Enum):
    CHARTER = "charter"
    PLAN = "plan"
    DECISION = "decision"
    EXPERIMENT = "experiment"
    REPORT = "report"
    PAPER_NOTE = "paper_note"
    CODE_DOC = "code_doc"
    OTHER = "other"


class DocumentAuthority(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    EXCLUDED = "excluded"


class ParseStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ClassificationSource(str, Enum):
    RULE = "rule"
    MODEL = "model"
    USER = "user"


class WorkItemKind(str, Enum):
    RESEARCH_QUESTION = "research_question"
    HYPOTHESIS = "hypothesis"
    MILESTONE = "milestone"
    EXPERIMENT = "experiment"
    DECISION = "decision"
    ACTION = "action"


class DeclaredStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ObservedStatus(str, Enum):
    NO_EVIDENCE = "no_evidence"
    ACTIVE = "active"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"


class InferredStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


class SnapshotTrigger(str, Enum):
    INITIAL = "initial"
    FILE_CHANGE = "file_change"
    GIT_CHANGE = "git_change"
    MANUAL = "manual"
    JOB_COMPLETE = "job_complete"
    SCHEDULED = "scheduled"


class ReviewKind(str, Enum):
    PLAN_DRIFT = "plan_drift"
    EVIDENCE_CHANGE = "evidence_change"
    NEW_PAPER = "new_paper"
    RUN_FAILURE = "run_failure"
    INDEX_STALE = "index_stale"
    DOCUMENT_AUTHORITY = "document_authority"
    STATUS_SUGGESTION = "status_suggestion"
    BRANCH_DIVERGENCE = "branch_divergence"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    SUPERSEDED = "superseded"


class EventKind(str, Enum):
    DOCUMENT_DISCOVERED = "document.discovered"
    DOCUMENT_CHANGED = "document.changed"
    GIT_HEAD_CHANGED = "git.head_changed"
    GIT_WORKTREE_CHANGED = "git.worktree_changed"
    TEST_COMPLETED = "test.completed"
    ARTIFACT_CREATED = "artifact.created"
    RESEARCH_QUERY_COMPLETED = "research_query.completed"
    PAPER_RADAR_COMPLETED = "paper_radar.completed"
    PAPER_SAVED = "paper.saved"
    KNOWLEDGE_INDEX_CHANGED = "knowledge.index_changed"
    EVIDENCE_SOURCE_CHANGED = "evidence.source_changed"
    WORK_ITEM_CONFIRMED = "work_item.confirmed"
    REVIEW_RESOLVED = "review.resolved"


class ProjectDocument(BaseModel):
    """A discovered or confirmed document in a project (P3 §5.2)."""

    document_id: str = Field(description="Stable id (hash of project_id + relative path)")
    project_id: str
    path: str
    content_hash: str = ""
    kind: DocumentKind = DocumentKind.OTHER
    authority: DocumentAuthority = DocumentAuthority.CANDIDATE
    parse_status: ParseStatus = ParseStatus.PENDING
    language: str = ""
    title: str = ""
    modified_at: float = 0.0
    indexed_at: float = 0.0
    extractor_version: str = ""
    classification_source: ClassificationSource = ClassificationSource.RULE
    classification_confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchWorkItem(BaseModel):
    """Smallest research work object (P3 §5.3)."""

    work_item_id: str
    project_id: str
    kind: WorkItemKind = WorkItemKind.ACTION
    title: str
    parent_id: str = ""
    declared_status: DeclaredStatus = DeclaredStatus.PLANNED
    observed_status: ObservedStatus = ObservedStatus.NO_EVIDENCE
    inferred_status: InferredStatus = InferredStatus.NEEDS_REVIEW
    acceptance_criteria: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    linked_branch: str = ""
    linked_run_ids: list[str] = Field(default_factory=list)
    linked_paper_keys: list[str] = Field(default_factory=list)
    updated_at: float = 0.0


class GitState(BaseModel):
    is_repository: bool = False
    root: str = ""
    branch: str = ""
    head: str = ""
    dirty_files: int = 0
    ahead: int | None = None
    behind: int | None = None
    checked_at: float = 0.0


class ProjectContextSnapshot(BaseModel):
    """Immutable, comparable versioned project state (P3 §5.4)."""

    snapshot_id: str
    project_id: str
    revision: int
    created_at: float
    trigger: SnapshotTrigger = SnapshotTrigger.INITIAL
    definition_version: str = ""
    document_index_version: str = ""
    git_state: GitState = Field(default_factory=GitState)
    work_items: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_state: dict[str, Any] = Field(default_factory=dict)
    research_state: dict[str, Any] = Field(default_factory=dict)
    run_state: dict[str, Any] = Field(default_factory=dict)
    evidence_state: dict[str, Any] = Field(default_factory=dict)
    health: str = "ok"
    summary: dict[str, Any] = Field(default_factory=dict)


class ProjectEvent(BaseModel):
    """Normalized event consumed by the state builder (P3 §5.5)."""

    event_id: str = ""
    project_id: str
    kind: EventKind
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: float = 0.0
    dedup_key: str = Field(
        default="",
        description="Idempotency key; empty = event_id itself",
    )


class ReviewItem(BaseModel):
    """Unified review-queue item (P3 §5.6)."""

    review_id: str
    project_id: str
    kind: ReviewKind
    priority: int = 50
    status: ReviewStatus = ReviewStatus.PENDING
    summary: str = ""
    impact_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    proposed_action: str = ""
    input_snapshot_id: str = ""
    created_at: float = 0.0
    resolved_at: float = 0.0


def utc_now() -> float:
    return time.time()


def new_event(
    project_id: str,
    kind: EventKind,
    *,
    payload: dict[str, Any] | None = None,
    dedup_key: str = "",
) -> ProjectEvent:
    if not dedup_key:
        import uuid

        dedup_key = f"auto-{uuid.uuid4().hex[:16]}"
    return ProjectEvent(
        project_id=project_id,
        kind=kind,
        payload=payload or {},
        created_at=utc_now(),
        dedup_key=dedup_key,
    )


def new_snapshot(
    project_id: str,
    *,
    revision: int = 1,
    trigger: SnapshotTrigger = SnapshotTrigger.INITIAL,
) -> ProjectContextSnapshot:
    return ProjectContextSnapshot(
        snapshot_id=f"{project_id}:{revision}",
        project_id=project_id,
        revision=revision,
        created_at=utc_now(),
        trigger=trigger,
    )
