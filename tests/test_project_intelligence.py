"""P3.0+P3.1 — project intelligence protocol, repositories, event/snapshot
state building, idempotency, restart recovery, and legacy adapter."""

from __future__ import annotations

import json
import time
from pathlib import Path

from conflux.adapters.sqlite_store import SQLiteDatabase
from conflux.projects import (
    P3_PROTOCOL_VERSION,
    PROJECT_INTELLIGENCE_STATEMENTS,
    DeclaredStatus,
    DocumentAuthority,
    DocumentKind,
    EventKind,
    ProjectContextSnapshot,
    ProjectDocument,
    ProjectEvent,
    ProjectIntelligence,
    ProjectStateApplication,
    ResearchWorkItem,
    ReviewItem,
    ReviewKind,
    SnapshotTrigger,
    build_snapshot,
    ingest_events,
    new_event,
    new_snapshot,
    register_project_intelligence_migration,
)
from conflux.project_registry.models import ProjectDefinition


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    db.bootstrap_schema()
    return db


def _intelligence(db: SQLiteDatabase) -> ProjectIntelligence:
    intelligence = ProjectIntelligence(db)
    intelligence.ensure_schema()
    return intelligence


def _project() -> ProjectDefinition:
    project = ProjectDefinition(id="p3-test", name="P3 Test", path=".")
    project.plan.overall_goal = "P3 test project"
    return project


# ── P3.0 protocol ────────────────────────────────────────────────


def test_protocol_contracts_round_trip():
    event = new_event("p1", EventKind.GIT_HEAD_CHANGED, payload={"head": "abc"})
    assert event.kind.value == "git.head_changed"
    assert event.dedup_key  # auto dedup key assigned
    snapshot = new_snapshot("p1", revision=1)
    assert snapshot.snapshot_id == "p1:1"
    assert snapshot.trigger == SnapshotTrigger.INITIAL
    item = ResearchWorkItem(
        work_item_id="w1", project_id="p1", kind="milestone", title="M",
        declared_status=DeclaredStatus.IN_PROGRESS,
    )
    assert item.declared_status.value == "in_progress"
    assert P3_PROTOCOL_VERSION.startswith("conflux.dev/p3/")
    # JSON serialization must round-trip (wire format is JSON).
    payload = json.loads(event.model_dump_json())
    assert payload["kind"] == "git.head_changed"


def test_migration_registered_globally():
    from conflux.adapters import sqlite_store as store

    versions = {item[0] for item in store.SCHEMA_MIGRATIONS}
    assert "0007_project_intelligence" in versions
    assert "0008_project_cycles" in versions
    assert store.SCHEMA_MIGRATIONS[-1][0] == "0008_project_cycles"


def test_bootstrap_applies_project_intelligence(tmp_path: Path):
    db = _db(tmp_path)
    assert db.schema_version() == len(
        [item for item in __import__("conflux.adapters.sqlite_store", fromlist=["SCHEMA_MIGRATIONS"]).SCHEMA_MIGRATIONS]
    )
    table = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='project_events'"
    ).fetchone()
    assert table is not None


# ── P3.1 repositories ────────────────────────────────────────────


def test_event_store_append_and_idempotent(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    event = new_event("p1", EventKind.GIT_HEAD_CHANGED, payload={"head": "h1"}, dedup_key="git-h1")
    event_id = intelligence.events.append(event)
    assert event_id
    # Same dedup_key -> duplicate rejected (idempotent).
    assert intelligence.events.append(event) == ""
    assert intelligence.events.count("p1") == 1
    rows = intelligence.events.list("p1")
    assert rows[0]["payload"]["head"] == "h1"


def test_snapshot_store_round_trip_and_immutability(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    snapshot = new_snapshot("p1", revision=1)
    snapshot.git_state.branch = "main"
    snapshot.git_state.head = "abc123"
    snapshot.health = "warning"
    intelligence.snapshots.save(snapshot)
    latest = intelligence.snapshots.latest("p1")
    assert latest is not None
    assert latest.revision == 1
    assert latest.git_state.branch == "main"
    assert latest.git_state.head == "abc123"
    assert latest.health == "warning"
    # Immutable: a new save does not overwrite the old revision.
    v2 = new_snapshot("p1", revision=2)
    intelligence.snapshots.save(v2)
    assert intelligence.snapshots.get("p1", 1).git_state.head == "abc123"
    current = intelligence.snapshots.current("p1")
    assert current["revision"] == 2


def test_work_item_and_review_stores(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    item = ResearchWorkItem(work_item_id="w1", project_id="p1", kind="milestone", title="M")
    intelligence.work_items.upsert(item)
    assert intelligence.work_items.get("w1").title == "M"
    review = ReviewItem(review_id="r1", project_id="p1", kind=ReviewKind.PLAN_DRIFT, summary="drift")
    intelligence.reviews.create(review)
    pending = intelligence.reviews.list("p1", status="pending")
    assert len(pending) == 1
    assert intelligence.reviews.resolve("r1", "confirmed") is True
    assert intelligence.reviews.list("p1", status="confirmed")[0].status.value == "confirmed"


def test_document_store_authority(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    doc = ProjectDocument(
        document_id="d1", project_id="p1", path="docs/PLAN.md",
        kind=DocumentKind.PLAN, authority=DocumentAuthority.CANDIDATE,
    )
    intelligence.documents.upsert(doc)
    assert intelligence.documents.get("d1").kind.value == "plan"
    assert intelligence.documents.set_authority("d1", "confirmed") is True
    assert intelligence.documents.get("d1").authority.value == "confirmed"


# ── P3.1 state builder ───────────────────────────────────────────


def test_build_snapshot_consumes_events(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    project = _project()
    events = [
        new_event("p3-test", EventKind.GIT_HEAD_CHANGED,
                  payload={"root": ".", "branch": "main", "head": "h1"},
                  dedup_key="git-h1"),
        new_event("p3-test", EventKind.RESEARCH_QUERY_COMPLETED,
                  payload={"run_id": "r1", "status": "completed"},
                  dedup_key="run-r1"),
    ]
    ingest_events(intelligence, events)
    snapshot = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    assert snapshot.revision == 1
    assert snapshot.git_state.branch == "main"
    assert snapshot.run_state["runs"][0]["run_id"] == "r1"
    assert snapshot.trigger == SnapshotTrigger.MANUAL
    # Second build: no new events, revision bumps, state preserved.
    v2 = build_snapshot(intelligence, project, trigger=SnapshotTrigger.SCHEDULED)
    assert v2.revision == 2
    assert v2.git_state.branch == "main"


def test_build_snapshot_idempotent_events(tmp_path: Path):
    """Re-ingesting the same dedup-key events must not duplicate state."""
    intelligence = _intelligence(_db(tmp_path))
    project = _project()
    events = [
        new_event("p3-test", EventKind.RESEARCH_QUERY_COMPLETED,
                  payload={"run_id": "r1", "status": "completed"},
                  dedup_key="run-r1"),
    ]
    ingest_events(intelligence, events)
    # Same events again -> no new rows.
    assert ingest_events(intelligence, events) == 0
    snapshot = build_snapshot(intelligence, project)
    assert len(snapshot.run_state["runs"]) == 1


def test_restart_recovery(tmp_path: Path):
    """A fresh connection on the same file recovers events + snapshots."""
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    ingest_events(intelligence, [
        new_event("p3-test", EventKind.EVIDENCE_SOURCE_CHANGED,
                  payload={"source_id": "s1"}, dedup_key="ev-s1"),
    ])
    build_snapshot(intelligence, project)
    db.close()
    # Reopen the same file.
    db2 = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    intelligence2 = ProjectIntelligence(db2)
    assert intelligence2.events.count("p3-test") == 1
    latest = intelligence2.snapshots.latest("p3-test")
    assert latest is not None
    assert len(latest.evidence_state["sources"]) == 1


# ── P3.1 collectors + application ────────────────────────────────


def test_collect_git_events(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    # A non-repo dir yields no git events (deterministic, no crash).
    project = ProjectDefinition(id="plain", name="Plain", path=str(tmp_path / "plain"))
    (tmp_path / "plain").mkdir(exist_ok=True)
    from conflux.projects.collectors import collect_git_events

    events = collect_git_events(project, check_remote=False)
    assert events == []


def test_application_refresh_and_state(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    app = ProjectStateApplication(intelligence)
    project = _project()
    result = app.refresh(project, force=True)
    assert result["ok"] is True
    assert result["project_id"] == "p3-test"
    assert result["revision"] == 1
    state = app.state("p3-test")
    assert state is not None
    assert state["project_id"] == "p3-test"
    assert app.revisions("p3-test")[0]["revision"] == 1




# ── P3.6 replay cursor + partition caps ────────────────────────────


def test_incremental_replay_uses_cursor_and_caps_partitions(tmp_path: Path):
    """>1000 events: batched replay, bounded partitions, cursor advances."""
    intelligence = _intelligence(_db(tmp_path))
    project = _project()
    first = build_snapshot(intelligence, project)
    assert first.event_cursor == 0

    # 1200 run events: far beyond the old single-fetch 1000-event limit.
    for index in range(1200):
        intelligence.events.append(new_event(
            "p3-test", EventKind.RESEARCH_QUERY_COMPLETED,
            payload={"run_id": f"run-{index:04d}", "status": "completed",
                     "work_item_id": "", "elapsed_seconds": 1.0},
        ))
    second = build_snapshot(intelligence, project)
    runs = second.run_state.get("runs") or []
    assert len(runs) == 200  # capped, newest survive
    assert runs[-1]["run_id"] == "run-1199"
    assert second.event_cursor == 1200

    # One new event -> cursor advances by exactly one, state stays bounded.
    intelligence.events.append(new_event(
        "p3-test", EventKind.GIT_HEAD_CHANGED,
        payload={"root": ".", "branch": "main", "head": "h2",
                 "recent_subjects": ["x"], "checked_at": time.time()},
    ))
    third = build_snapshot(intelligence, project)
    assert third.event_cursor == 1201
    assert third.git_state.head == "h2"
    assert len(third.run_state.get("runs") or []) == 200


def test_force_rebuild_replays_full_log(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    project = _project()
    build_snapshot(intelligence, project)
    for index in range(20):
        intelligence.events.append(new_event(
            "p3-test", EventKind.RESEARCH_QUERY_COMPLETED,
            payload={"run_id": f"r{index}", "status": "completed"},
        ))
    build_snapshot(intelligence, project)
    forced = build_snapshot(intelligence, project, force=True)
    assert len(forced.run_state.get("runs") or []) == 20
    assert forced.event_cursor == 20
