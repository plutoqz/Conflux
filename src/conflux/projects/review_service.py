"""P3.3 deterministic review seeding (plan §5.6/§9.3).

Rules only propose candidates for the unified inbox — nothing here writes
declared state or document authority.  Review ids are deterministic hashes,
so seeding is idempotent under replay and never duplicates.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .contracts import ReviewItem, ReviewKind, ReviewStatus
from .repository import ProjectIntelligence

# Priority by impact/uncertainty/timeliness (plan §5.6); model never assigns.
_PRIORITY_AUTHORITY = 80
_PRIORITY_RUN_FAILURE = 70
_PRIORITY_STALE = 60


def _review_id(project_id: str, subject: str) -> str:
    digest = hashlib.sha256(f"{project_id}|{subject}".encode("utf-8")).hexdigest()[:16]
    return f"r-{digest}"


def _existing(intelligence: ProjectIntelligence, project_id: str, review_id: str) -> ReviewItem | None:
    for review in intelligence.reviews.list(project_id):
        if review.review_id == review_id:
            return review
    return None


def seed_reviews(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    input_snapshot_id: str = "",
) -> list[ReviewItem]:
    """Create (once) deterministic reviews; existing items keep their status."""
    project_id = project.id
    created: list[ReviewItem] = []

    # 1) Rule-classified charter/plan documents awaiting authority confirmation.
    for doc in intelligence.documents.list(project_id):
        if doc.authority.value != "candidate" or doc.kind.value not in {"charter", "plan"}:
            continue
        review = ReviewItem(
            review_id=_review_id(project_id, f"doc-authority:{doc.document_id}"),
            project_id=project_id,
            kind=ReviewKind.DOCUMENT_AUTHORITY,
            priority=_PRIORITY_AUTHORITY,
            status=ReviewStatus.PENDING,
            summary=f"发现疑似项目纲领/计划文档，等待确权：{doc.path}",
            impact_refs=[doc.document_id],
            proposed_action="在“证据与知识”页确认该文档为权威来源，或标记排除",
            input_snapshot_id=input_snapshot_id,
            created_at=time.time(),
        )
        if _existing(intelligence, project_id, review.review_id) is None:
            intelligence.reviews.create(review)
            created.append(review)

    # 2) Confirmed documents whose content changed after confirmation (stale).
    for doc in intelligence.documents.list(project_id):
        if doc.authority.value != "confirmed":
            continue
        confirmed_hash = str((doc.metadata or {}).get("confirmed_hash") or "")
        if not confirmed_hash or confirmed_hash == doc.content_hash:
            continue
        review = ReviewItem(
            review_id=_review_id(project_id, f"doc-stale:{doc.document_id}"),
            project_id=project_id,
            kind=ReviewKind.DOCUMENT_AUTHORITY,
            priority=_PRIORITY_STALE,
            status=ReviewStatus.PENDING,
            summary=f"已确权文档内容发生变化：{doc.path}",
            impact_refs=[doc.document_id],
            proposed_action="复核该文档新内容，并重新确认或排除",
            input_snapshot_id=input_snapshot_id,
            created_at=time.time(),
        )
        if _existing(intelligence, project_id, review.review_id) is None:
            intelligence.reviews.create(review)
            created.append(review)

    # 3) Failed research runs -> run_failure reviews.
    failed_runs: set[str] = set()
    for event in intelligence.events.list(project_id, limit=1000):
        if str(event.get("kind") or "") != "research_query.completed":
            continue
        payload = event.get("payload") or {}
        if str(payload.get("status") or "") != "failed":
            continue
        run_id = str(payload.get("run_id") or "")
        if not run_id or run_id in failed_runs:
            continue
        failed_runs.add(run_id)
        review = ReviewItem(
            review_id=_review_id(project_id, f"run-failure:{run_id}"),
            project_id=project_id,
            kind=ReviewKind.RUN_FAILURE,
            priority=_PRIORITY_RUN_FAILURE,
            status=ReviewStatus.PENDING,
            summary=f"研究运行失败：{run_id}",
            impact_refs=[run_id],
            proposed_action="查看运行日志与失败原因，决定重试或调整查询",
            input_snapshot_id=input_snapshot_id,
            created_at=time.time(),
        )
        if _existing(intelligence, project_id, review.review_id) is None:
            intelligence.reviews.create(review)
            created.append(review)

    # Supersede stale failure reviews whose run no longer failed.
    for review in intelligence.reviews.list(project_id, status="pending"):
        if review.kind != ReviewKind.RUN_FAILURE:
            continue
        run_id = (review.impact_refs or [""])[0]
        if run_id and run_id not in failed_runs:
            intelligence.reviews.resolve(review.review_id, ReviewStatus.SUPERSEDED.value)

    return created


def supersede_document_reviews(
    intelligence: ProjectIntelligence,
    project_id: str,
    document_id: str,
) -> int:
    """Close pending authority reviews for a document once confirmed/excluded."""
    superseded = 0
    for review in intelligence.reviews.list(project_id, status="pending"):
        if review.kind != ReviewKind.DOCUMENT_AUTHORITY:
            continue
        if document_id in (review.impact_refs or []):
            intelligence.reviews.resolve(review.review_id, ReviewStatus.SUPERSEDED.value)
            superseded += 1
    return superseded
