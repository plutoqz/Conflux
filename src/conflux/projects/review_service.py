"""P3.3/P3.4 deterministic review seeding (plan §5.6/§9.3/§10).

Rules only propose candidates for the unified inbox — nothing here writes
declared state or document authority.  Review ids are deterministic hashes,
so seeding is idempotent under replay and never duplicates.

P3.4 producers: status suggestions (completion without evidence /
contradicting claims), branch association + divergence, and new-paper
notices routed through radar intents.
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .contracts import ReviewItem, ReviewKind, ReviewStatus
from .link_service import persist_links
from .repository import ProjectIntelligence

# Priority by impact/uncertainty/timeliness (plan §5.6); model never assigns.
_PRIORITY_AUTHORITY = 80
_PRIORITY_RUN_FAILURE = 70
_PRIORITY_STALE = 60
_PRIORITY_STATUS = 55
_PRIORITY_BRANCH = 50
_PRIORITY_NEW_PAPER = 45


def _review_id(project_id: str, subject: str) -> str:
    digest = hashlib.sha256(f"{project_id}|{subject}".encode("utf-8")).hexdigest()[:16]
    return f"r-{digest}"


def _existing(intelligence: ProjectIntelligence, project_id: str, review_id: str) -> ReviewItem | None:
    for review in intelligence.reviews.list(project_id):
        if review.review_id == review_id:
            return review
    return None


def _add_review(
    intelligence: ProjectIntelligence,
    *,
    project_id: str,
    subject: str,
    kind: ReviewKind,
    priority: int,
    summary: str,
    proposed_action: str,
    impact_refs: list[str] | None = None,
    input_snapshot_id: str = "",
) -> ReviewItem | None:
    review = ReviewItem(
        review_id=_review_id(project_id, subject),
        project_id=project_id,
        kind=kind,
        priority=priority,
        status=ReviewStatus.PENDING,
        summary=summary,
        impact_refs=list(impact_refs or []),
        proposed_action=proposed_action,
        input_snapshot_id=input_snapshot_id,
        created_at=time.time(),
    )
    if _existing(intelligence, project_id, review.review_id) is None:
        intelligence.reviews.create(review)
        return review
    return None


def _work_items_with_links(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
) -> list[dict[str, Any]]:
    try:
        return persist_links(intelligence, project)
    except Exception:
        from .projections import work_item_projection

        return work_item_projection(project)


def seed_reviews(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    input_snapshot_id: str = "",
    rag: dict[str, Any] | None = None,
) -> list[ReviewItem]:
    """Create (once) deterministic reviews; existing items keep their status.

    ``rag`` (P3.4): RAG coverage result; stale documents become index_stale
    reviews.
    """
    project_id = project.id
    created: list[ReviewItem] = []

    # 1.5) Indexed documents whose content changed since indexing (P3.4).
    if rag and rag.get("by_document"):
        by_path = {
            str(doc.path): doc.document_id for doc in intelligence.documents.list(project_id)
        }
        for path, status in rag["by_document"].items():
            if status != "stale":
                continue
            document_id = by_path.get(path, "")
            if not document_id:
                continue
            review = ReviewItem(
                review_id=_review_id(project_id, f"index-stale:{document_id}"),
                project_id=project_id,
                kind=ReviewKind.INDEX_STALE,
                priority=_PRIORITY_STALE,
                status=ReviewStatus.PENDING,
                summary=f"已索引文档内容变化，知识库覆盖过期：{path}",
                impact_refs=[document_id],
                proposed_action="在“证据与知识”页重新索引该文档，或标记排除",
                input_snapshot_id=input_snapshot_id,
                created_at=time.time(),
            )
            if _existing(intelligence, project_id, review.review_id) is None:
                intelligence.reviews.create(review)
                created.append(review)

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

    # ── P3.4 producers ─────────────────────────────────────────────
    items = _work_items_with_links(intelligence, project)
    seeded: list[ReviewItem] = []

    # 4) Status suggestions: completion without evidence, or evidence that
    #    contradicts the declared status (evidence before status, §4.2).
    for item in items:
        work_item_id = item["work_item_id"]
        declared = item.get("declared_status") or ""
        evidence = item.get("evidence_refs") or []
        negative = [ref for ref in evidence if ":contradicts:" in ref or ":insufficient:" in ref]
        if declared == "completed" and not evidence:
            seeded.append(_add_review(
                intelligence,
                project_id=project_id,
                subject=f"status-no-evidence:{work_item_id}",
                kind=ReviewKind.STATUS_SUGGESTION,
                priority=_PRIORITY_STATUS,
                summary=f"工作项「{item['title']}」标记为已完成，但没有关联证据",
                proposed_action="在“研究工作”页发起研究补齐证据，或人工调整状态",
                impact_refs=[work_item_id],
                input_snapshot_id=input_snapshot_id,
            ))
        if negative:
            seeded.append(_add_review(
                intelligence,
                project_id=project_id,
                subject=f"status-contradicted:{work_item_id}",
                kind=ReviewKind.STATUS_SUGGESTION,
                priority=_PRIORITY_STATUS,
                summary=f"工作项「{item['title']}」的证据包含不支持结论（{len(negative)} 条）",
                proposed_action="复核证据与验收标准，决定补充证据或调整状态",
                impact_refs=[work_item_id],
                input_snapshot_id=input_snapshot_id,
            ))

    # Supersede "completion without evidence" suggestions once evidence lands
    # (contradiction suggestions stay — the evidence is exactly the problem).
    for review in intelligence.reviews.list(project_id, status="pending"):
        if review.kind != ReviewKind.STATUS_SUGGESTION:
            continue
        if "没有关联证据" not in review.summary:
            continue
        work_item_id = (review.impact_refs or [""])[0]
        item = next((candidate for candidate in items if candidate["work_item_id"] == work_item_id), None)
        if item and (item.get("evidence_refs") or []):
            intelligence.reviews.resolve(review.review_id, ReviewStatus.SUPERSEDED.value)

    # 5) Branch association suggestions + divergence (plan §10.4).
    git_events = [event for event in intelligence.events.list(project_id, limit=200)
                  if str(event.get("kind") or "") == "git.head_changed"]
    if git_events:
        latest_git = (git_events[-1].get("payload") or {})
        branch = str(latest_git.get("branch") or "")
        latest_snapshot = intelligence.snapshots.latest(project_id)
        dirty = int(latest_snapshot.git_state.dirty_files) if latest_snapshot else 0
        subjects = [str(item).casefold() for item in latest_git.get("recent_subjects") or []]
        branch_tokens = set(re.findall(r"[a-z0-9]+", branch.casefold())) if branch else set()
        for item in items:
            if item.get("declared_status") != "in_progress":
                continue
            work_item_id = item["work_item_id"]
            title_tokens = set(re.findall(r"[a-z0-9]+", (item["title"] or "").casefold()))
            keyword_hit = bool(branch_tokens & title_tokens and title_tokens) or any(
                token in " ".join(subjects) for token in title_tokens if len(token) >= 4
            )
            if item.get("linked_branch"):
                ahead = latest_git.get("ahead")
                behind = latest_git.get("behind")
                if dirty or ahead or behind:
                    seeded.append(_add_review(
                        intelligence,
                        project_id=project_id,
                        subject=f"branch-diverged:{work_item_id}",
                        kind=ReviewKind.BRANCH_DIVERGENCE,
                        priority=_PRIORITY_BRANCH,
                        summary=(
                            f"工作项「{item['title']}」关联分支 {item['linked_branch']} 存在"
                            f"{'未提交变更' if dirty else ''}"
                            f"{'，领先 ' + str(ahead) if ahead else ''}"
                            f"{'，落后 ' + str(behind) if behind else ''}"
                        ),
                        proposed_action="提交/同步分支，或解除分支关联",
                        impact_refs=[work_item_id],
                        input_snapshot_id=input_snapshot_id,
                    ))
            elif keyword_hit:
                seeded.append(_add_review(
                    intelligence,
                    project_id=project_id,
                    subject=f"branch-suggest:{work_item_id}",
                    kind=ReviewKind.BRANCH_DIVERGENCE,
                    priority=_PRIORITY_BRANCH,
                    summary=f"建议把当前分支 {branch or 'detached'} 关联到工作项「{item['title']}」",
                    proposed_action="确认分支关联（写入项目状态），或忽略该建议",
                    impact_refs=[work_item_id],
                    input_snapshot_id=input_snapshot_id,
                ))

    # 6) New papers for intents linked to work items (plan §10.1).
    try:
        from conflux.adapters.sqlite_store import ProjectPaperStore

        papers = ProjectPaperStore(intelligence.db).list(project_id)
    except Exception:
        papers = []
    new_paper_notices = 0
    for item in items:
        work_item_id = item["work_item_id"]
        linked_papers = set(item.get("linked_paper_keys") or [])
        for paper in papers or []:
            if str(paper.get("status") or "") != "shortlisted":
                continue
            paper_key = str(paper.get("paper_key") or "")
            if paper_key in linked_papers or new_paper_notices >= 5:
                continue
            seeded.append(_add_review(
                intelligence,
                project_id=project_id,
                subject=f"new-paper:{paper_key}:{work_item_id}",
                kind=ReviewKind.NEW_PAPER,
                priority=_PRIORITY_NEW_PAPER,
                summary=f"工作项「{item['title']}」有新候选论文等待评审",
                proposed_action="在论文雷达中评审并决定保存或忽略",
                impact_refs=[paper_key],
                input_snapshot_id=input_snapshot_id,
            ))
            new_paper_notices += 1

    created.extend(review for review in seeded if review is not None)
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
