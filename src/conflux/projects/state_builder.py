"""P3.1 state builder — consume normalized events, produce snapshots.

The builder reads the latest snapshot, applies new events incrementally
(recomputing only affected partitions), runs deterministic health rules, and
writes an immutable snapshot plus the materialized current state
(plan §9.2).  It never invokes the model and never writes declared state.
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
            checked_at=float(payload.get("checked_at") or 0),
        )
    elif kind == "git.worktree_changed":
        snapshot.git_state.dirty_files = int(payload.get("dirty_files") or 0)
    elif kind == "research_query.completed":
        runs = snapshot.run_state.setdefault("runs", [])
        run_id = str(payload.get("run_id") or "")
        if run_id and all(str(r.get("run_id") or "") != run_id for r in runs):
            runs.append(payload)
    elif kind == "evidence.source_changed":
        sources = snapshot.evidence_state.setdefault("sources", [])
        source_id = str(payload.get("source_id") or "")
        if source_id and all(str(s.get("source_id") or "") != source_id for s in sources):
            sources.append(payload)
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


def build_snapshot(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    trigger: SnapshotTrigger = SnapshotTrigger.SCHEDULED,
    force: bool = False,
) -> ProjectContextSnapshot:
    """Build the next snapshot from the latest one + new events."""
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

    snapshot.health = _health_from_snapshot(snapshot)
    snapshot.summary = {
        "revision": snapshot.revision,
        "event_count": len(events),
        "work_item_count": len(snapshot.work_items),
        "git": {
            "branch": snapshot.git_state.branch,
            "head": snapshot.git_state.head,
            "dirty_files": snapshot.git_state.dirty_files,
        },
    }
    intelligence.snapshots.save(snapshot)
    return snapshot
