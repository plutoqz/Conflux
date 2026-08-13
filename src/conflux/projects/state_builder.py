"""P3.1 state builder — consume normalized events, produce snapshots.

The builder reads the latest snapshot, applies new events incrementally
(recomputing only affected partitions), runs deterministic health rules, and
writes an immutable snapshot plus the materialized current state
(plan §9.2).  It never invokes the model and never writes declared state.

P3.3: partitions that are deterministic projections (work items from the
YAML plan, knowledge state from the document index) are recomputed here so
the page payload stays a single materialized read.
"""

from __future__ import annotations

import time
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .contracts import (
    GitState,
    ProjectContextSnapshot,
    SnapshotTrigger,
    new_snapshot,
)
from .link_service import persist_links
from .projections import knowledge_state
from .repository import ProjectIntelligence


def _apply_event_to_snapshot(
    snapshot: ProjectContextSnapshot,
    event: dict[str, Any],
) -> None:
    kind = str(event.get("kind") or "")
    payload = event.get("payload") or {}
    if kind == "git.head_changed":
        snapshot.git_state = GitState(
            is_repository=True,
            root=str(payload.get("root") or ""),
            branch=str(payload.get("branch") or ""),
            head=str(payload.get("head") or ""),
            ahead=payload.get("ahead") if payload.get("ahead") is not None else None,
            behind=payload.get("behind") if payload.get("behind") is not None else None,
            checked_at=float(payload.get("checked_at") or 0),
        )
    elif kind == "git.worktree_changed":
        snapshot.git_state.dirty_files = int(payload.get("dirty_files") or 0)
    elif kind == "research_query.completed":
        runs = snapshot.run_state.setdefault("runs", [])
        run_id = str(payload.get("run_id") or "")
        if run_id and all(str(r.get("run_id") or "") != run_id for r in runs):
            runs.append(payload)
    elif kind == "test.completed":
        # Append-only observation; the cycle audit compares per-period entries.
        # Keyed like the event dedup key so full replay never duplicates.
        tests = snapshot.run_state.setdefault("tests", [])
        key = (
            str(payload.get("command") or ""),
            str(payload.get("head") or ""),
            str(payload.get("status") or ""),
            payload.get("exit_code"),
        )
        if all((
            str(t.get("command") or ""),
            str(t.get("head") or ""),
            str(t.get("status") or ""),
            t.get("exit_code"),
        ) != key for t in tests):
            tests.append(payload)
    elif kind == "evidence.source_changed":
        sources = snapshot.evidence_state.setdefault("sources", [])
        source_id = str(payload.get("source_id") or "")
        if source_id and all(str(s.get("source_id") or "") != source_id for s in sources):
            sources.append(payload)
    elif kind == "paper_radar.completed":
        snapshot.research_state["radar"] = {
            "run_id": str(payload.get("run_id") or ""),
            "status": str(payload.get("status") or ""),
            "tokens": int(payload.get("tokens") or 0),
        }
    elif kind == "document.discovered" or kind == "document.changed":
        snapshot.document_index_version = str(
            payload.get("index_version") or snapshot.document_index_version
        )


def _health_from_snapshot(snapshot: ProjectContextSnapshot) -> str:
    if snapshot.git_state.is_repository and snapshot.git_state.dirty_files:
        return "warning"
    if snapshot.run_state.get("runs"):
        failed = [r for r in snapshot.run_state["runs"] if str(r.get("status") or "") == "failed"]
        if failed:
            return "warning"
    return "ok"


def _summary_from_snapshot(
    snapshot: ProjectContextSnapshot,
    *,
    pending_review_count: int,
    event_count: int,
) -> dict[str, Any]:
    """Deterministic first-screen summary (plan §7.2)."""
    items = snapshot.work_items or []
    milestones = [item for item in items if item.get("kind") == "milestone"]
    in_progress = [item for item in milestones if item.get("declared_status") == "in_progress"]
    blocked = [item for item in items if item.get("declared_status") == "blocked"]
    planned = [item for item in milestones if item.get("declared_status") == "planned"]
    actions = [item for item in items if item.get("kind") == "action"]
    goal = next((item for item in items if item.get("kind") == "research_question"), None)
    focus_candidates = in_progress + planned + blocked + actions
    focus = focus_candidates[0] if focus_candidates else (goal or (milestones[0] if milestones else None))
    next_actions = [
        item for item in items if item.get("kind") == "action"
    ][:3]
    runs = snapshot.run_state.get("runs") or []
    return {
        "revision": snapshot.revision,
        "focus": (focus or {}).get("title", "") if focus else "",
        "focus_kind": (focus or {}).get("kind", "") if focus else "",
        "in_progress": [item["title"] for item in in_progress],
        "blocked": [item["title"] for item in blocked],
        "next_actions": [item["title"] for item in next_actions],
        "pending_review_count": pending_review_count,
        "run_count": len(runs),
        "event_count": event_count,
        "git": {
            "branch": snapshot.git_state.branch,
            "head": snapshot.git_state.head,
            "dirty_files": snapshot.git_state.dirty_files,
        },
    }


def build_snapshot(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    trigger: SnapshotTrigger = SnapshotTrigger.SCHEDULED,
    force: bool = False,
    rag: dict[str, Any] | None = None,
) -> ProjectContextSnapshot:
    """Build the next snapshot from the latest one + new events.

    ``rag`` is the P3.4 RAG-coverage result computed during refresh; it is
    materialized into knowledge_state so page reads never touch Chroma.
    """
    latest = intelligence.snapshots.latest(project.id)
    if latest is None:
        snapshot = new_snapshot(project.id, revision=1, trigger=trigger)
    else:
        revision = latest.revision + 1
        snapshot = ProjectContextSnapshot(
            snapshot_id=f"{project.id}:{revision}",
            project_id=project.id,
            revision=revision,
            created_at=time.time(),
            trigger=trigger,
            definition_version=latest.definition_version,
            document_index_version=latest.document_index_version,
            git_state=latest.git_state,
            work_items=list(latest.work_items),
            knowledge_state=dict(latest.knowledge_state),
            research_state=dict(latest.research_state),
            run_state=dict(latest.run_state),
            evidence_state=dict(latest.evidence_state),
            health=latest.health,
            summary=dict(latest.summary),
        )

    if latest is None or force:
        # Full rebuild path: reset partitions that event replay may not cover.
        snapshot.git_state = GitState()
        snapshot.run_state = {}
        snapshot.evidence_state = {}

    # Consume events since the latest snapshot.
    events = intelligence.events.list(project.id, after_event_id=0, limit=1000)
    for event in events:
        _apply_event_to_snapshot(snapshot, event)

    # Deterministic projections + links (P3.3/P3.4): declared plan ->
    # work items, cross-feature runs/claims/papers -> link fields,
    # document index -> knowledge state.  No model, no scan.
    snapshot.work_items = persist_links(intelligence, project)
    snapshot.knowledge_state = knowledge_state(intelligence, project.id)
    if rag is not None:
        snapshot.knowledge_state["rag"] = dict(rag)

    pending_reviews = intelligence.reviews.list(project.id, status="pending")
    snapshot.summary = _summary_from_snapshot(
        snapshot,
        pending_review_count=len(pending_reviews),
        event_count=len(events),
    )
    snapshot.health = _health_from_snapshot(snapshot)
    if snapshot.summary.get("blocked"):
        snapshot.health = "warning"
    intelligence.snapshots.save(snapshot)
    return snapshot
