"""P3.1 collectors — turn existing sources into normalized ProjectEvents.

Each collector is deterministic and idempotent: it reads current facts from
the existing stores (git state, search runs, evidence ledger) and appends
normalized events with stable dedup keys, so replaying never duplicates
state (plan §9.1).
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .contracts import EventKind, ProjectEvent, new_event
from .repository import ProjectIntelligence


def _git_head_key(root: str, branch: str, head: str) -> str:
    digest = hashlib.sha256(f"{root}|{branch}|{head}".encode("utf-8")).hexdigest()[:16]
    return f"git-head-{digest}"


def _git_worktree_key(dirty_count: int) -> str:
    return f"git-worktree-dirty-{dirty_count}"


def collect_git_events(
    project: ProjectDefinition,
    *,
    check_remote: bool = False,
) -> list[ProjectEvent]:
    """Git head / worktree changes -> events (P3 §5.5 git.*)."""
    from conflux.progress_audit.git_inspector import inspect_git

    root = str(project.path)
    inspection = inspect_git(root, check_remote=check_remote)
    events: list[ProjectEvent] = []
    if not inspection.is_repository:
        return events
    branch = str(inspection.branch or "")
    head = str(inspection.head or "")
    dirty_files = inspection.dirty_files or []
    dirty = len(dirty_files) if isinstance(dirty_files, list) else int(dirty_files or 0)
    if head:
        events.append(new_event(
            project.id,
            EventKind.GIT_HEAD_CHANGED,
            payload={"root": root, "branch": branch, "head": head, "checked_at": time.time()},
            dedup_key=_git_head_key(root, branch, head),
        ))
    if dirty:
        events.append(new_event(
            project.id,
            EventKind.GIT_WORKTREE_CHANGED,
            payload={"root": root, "dirty_files": dirty, "checked_at": time.time()},
            dedup_key=_git_worktree_key(dirty),
        ))
    return events


def collect_run_events(
    project: ProjectDefinition,
    db: Any,
    *,
    since: float = 0.0,
) -> list[ProjectEvent]:
    """Recent search runs -> research_query.completed events (P3 §5.5)."""
    from conflux.adapters.sqlite_store import SearchRunStore

    events: list[ProjectEvent] = []
    try:
        store = SearchRunStore(db)
        runs = store.list(project_id=project.id, limit=20)
    except Exception:
        return events
    for run in runs or []:
        run_id = str(run.get("run_id") or "")
        if not run_id:
            continue
        created = float(run.get("created_at") or 0)
        if created < since:
            continue
        events.append(new_event(
            project.id,
            EventKind.RESEARCH_QUERY_COMPLETED,
            payload={
                "run_id": run_id,
                "status": str(run.get("status") or ""),
                "query_count": int(run.get("query_count") or 0),
                "elapsed_seconds": float(run.get("elapsed_seconds") or 0),
            },
            dedup_key=f"run-{run_id}",
        ))
    return events


def collect_evidence_events(
    project: ProjectDefinition,
    db: Any,
    *,
    since: float = 0.0,
) -> list[ProjectEvent]:
    """Evidence ledger source changes -> evidence.source_changed (P3 §5.5)."""
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository

    events: list[ProjectEvent] = []
    try:
        repository = EvidenceLedgerRepository(db)
        rows = repository.list_recent(project_id=project.id, limit=20)
    except Exception:
        return events
    for row in rows or []:
        source_id = str(row.get("source_id") or row.get("id") or "")
        if not source_id:
            continue
        created = float(row.get("created_at") or 0)
        if created < since:
            continue
        events.append(new_event(
            project.id,
            EventKind.EVIDENCE_SOURCE_CHANGED,
            payload={
                "source_id": source_id,
                "status": str(row.get("status") or ""),
                "created_at": created,
            },
            dedup_key=f"evidence-{source_id}-{int(created)}",
        ))
    return events


def collect_all_events(
    project: ProjectDefinition,
    db: Any,
    *,
    since: float = 0.0,
    check_remote: bool = False,
) -> list[ProjectEvent]:
    events: list[ProjectEvent] = []
    events.extend(collect_git_events(project, check_remote=check_remote))
    events.extend(collect_run_events(project, db, since=since))
    events.extend(collect_evidence_events(project, db, since=since))
    return events


def ingest_events(
    intelligence: ProjectIntelligence,
    events: list[ProjectEvent],
) -> int:
    """Append events idempotently; returns count of new events."""
    added = 0
    for event in events:
        if intelligence.events.append(event):
            added += 1
    return added
