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
            payload={
                "root": root,
                "branch": branch,
                "head": head,
                "ahead": inspection.ahead,
                "behind": inspection.behind,
                "recent_subjects": [str(commit.subject) for commit in (inspection.recent_commits or [])[:10]],
                "checked_at": time.time(),
            },
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
    """Query jobs (RunStore metadata) + latest radar run -> completed events."""
    events: list[ProjectEvent] = []
    try:
        from conflux.adapters.sqlite_store import RunStore, SearchRunStore

        # Research query jobs: project scoped via run metadata.
        for run in RunStore(db).list(limit=100) or []:
            metadata = run.get("metadata") or {}
            if str(metadata.get("project_id") or "") != project.id:
                continue
            run_id = str(run.get("run_id") or "")
            status = str(run.get("status") or "")
            if not run_id or status not in {"completed", "completed_with_warnings", "failed"}:
                continue
            budget = metadata.get("budget_consumed") or {}
            events.append(new_event(
                project.id,
                EventKind.RESEARCH_QUERY_COMPLETED,
                payload={
                    "run_id": run_id,
                    "status": "failed" if status == "failed" else "completed",
                    "work_item_id": str(metadata.get("work_item_id") or ""),
                    "elapsed_seconds": float(budget.get("elapsed_ms") or 0) / 1000.0,
                    "tokens": {
                        "input": int(budget.get("input_tokens") or 0),
                        "output": int(budget.get("output_tokens") or 0),
                    },
                },
                dedup_key=f"run-{run_id}",
            ))
        # Paper radar: one latest run per project.
        latest = SearchRunStore(db).latest(project.id)
        if latest and latest.get("run_id"):
            events.append(new_event(
                project.id,
                EventKind.PAPER_RADAR_COMPLETED,
                payload={
                    "run_id": str(latest["run_id"]),
                    "status": str(latest.get("status") or "completed"),
                    "tokens": int((latest.get("stats") or {}).get("llm_total_tokens") or 0),
                },
                dedup_key=f"radar-{latest['run_id']}",
            ))
    except Exception:
        return events
    return events


def collect_test_events(
    project: ProjectDefinition,
    *,
    since: float = 0.0,
) -> list[ProjectEvent]:
    """Run the configured test command once and emit test.completed (P3.5).

    Tests are an explicit, user-triggered observation: never part of
    ``collect_all_events`` so routine refreshes stay fast.  The dedup key
    covers (command, head, status) so re-running the same failing/passing
    command records once per distinct outcome.
    """
    if not (project.test_command or "").strip():
        return []
    from conflux.progress_audit.git_inspector import inspect_git
    from conflux.progress_audit.test_inspector import inspect_tests

    inspection = inspect_git(str(project.path))
    head = str(inspection.head or "")
    result = inspect_tests(
        str(project.path),
        project.test_command,
        timeout_seconds=project.test_timeout_seconds,
    )
    command = str(result.command or project.test_command)
    return [new_event(
        project.id,
        EventKind.TEST_COMPLETED,
        payload={
            "command": command,
            "status": result.status,
            "exit_code": result.exit_code,
            "elapsed_ms": result.elapsed_ms,
            "head": head,
            "checked_at": time.time(),
        },
        dedup_key=f"test-{hashlib.sha256(command.encode('utf-8')).hexdigest()[:16]}"
                  f"-{head[:12]}-{result.status}-{result.exit_code}",
    )]


def collect_evidence_events(
    project: ProjectDefinition,
    db: Any,
    *,
    since: float = 0.0,
) -> list[ProjectEvent]:
    """Evidence ledger source snapshots -> evidence.source_changed (P3 §5.5)."""
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository

    events: list[ProjectEvent] = []
    try:
        repository = EvidenceLedgerRepository(db)
        rows = repository.list_source_snapshots(limit=200)
    except Exception:
        return events
    for row in rows or []:
        source_id = str(row.get("source_identity") or "")
        content_hash = str(row.get("content_hash") or "")
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
                "content_hash": content_hash,
                "status": str(row.get("status") or ""),
                "created_at": created,
            },
            dedup_key=f"evidence-{source_id}-{content_hash[:16]}",
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
