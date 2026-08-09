"""M3 persistence slice: runtime home, SQLite stores, and storage CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from conflux.adapters.sqlite_store import (
    ApprovalStore,
    ArtifactStore,
    EventStore,
    RunStore,
    SQLiteDatabase,
    SCHEMA_MIGRATIONS,
)
from conflux.core.contracts import ApprovalRequest, ArtifactRef, StepResult
from conflux.core.runtime_home import SUB_DIRECTORIES, database_path
from conflux.core.storage_cli import doctor_command, init_command, migrate_command


def test_init_creates_home_and_is_idempotent(tmp_path: Path) -> None:
    assert init_command(str(tmp_path)) == 0
    assert database_path(tmp_path).exists()
    for sub in SUB_DIRECTORIES:
        assert (tmp_path / sub).is_dir()

    marker = tmp_path / "config" / "user.toml"
    marker.write_text("keep=1", encoding="utf-8")
    assert init_command(str(tmp_path)) == 0
    assert marker.read_text(encoding="utf-8") == "keep=1"


def test_init_does_not_overwrite_existing_files(tmp_path: Path) -> None:
    existing = tmp_path / "objects" / "artifact.bin"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"original")
    init_command(str(tmp_path))
    assert existing.read_bytes() == b"original"


def test_migrate_dry_run_requires_init(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert migrate_command(str(tmp_path), dry_run=True) == 1
    output = capsys.readouterr().out
    assert "Run 'conflux init' first" in output


def test_migrate_dry_run_and_apply(tmp_path: Path) -> None:
    init_command(str(tmp_path))
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    assert db.schema_version() == len(SCHEMA_MIGRATIONS)
    db.close()

    assert migrate_command(str(tmp_path), dry_run=True) == 0
    assert migrate_command(str(tmp_path), dry_run=False) == 0


def test_migrate_without_migration_table_reports_every_pending_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    database_path(tmp_path).touch()

    assert migrate_command(str(tmp_path), dry_run=True) == 0

    output = capsys.readouterr().out
    for version, _ in SCHEMA_MIGRATIONS:
        assert version in output


def test_run_store_roundtrip_across_connections(tmp_path: Path) -> None:
    db_path = database_path(tmp_path)
    SQLiteDatabase(db_path).connect().bootstrap_schema()

    first = SQLiteDatabase(db_path).connect()
    runs = RunStore(first)
    run = runs.create_run(run_id="run-1", workspace="/tmp/work", metadata={"depth": "standard"})
    assert run["status"] == "running"
    runs.add_step(
        "run-1",
        StepResult.success({"answer": "ok"}, plugin_id="builtin.research", capability_id="synthesize"),
        step_id="step-1",
    )
    first.close()

    # A fresh connection simulates a process restart.
    second = SQLiteDatabase(db_path).connect()
    runs2 = RunStore(second)
    restored = runs2.get("run-1")
    assert restored is not None
    assert restored["metadata"] == {"depth": "standard"}
    assert runs2.steps("run-1")[0]["output"] == {"answer": "ok"}
    assert runs2.last_step("run-1")["step_id"] == "step-1"
    assert runs2.update_status("run-1", "completed") is True
    assert runs2.get("run-1")["status"] == "completed"
    second.close()


def test_event_store_reopen_and_incremental_read(tmp_path: Path) -> None:
    db_path = database_path(tmp_path)
    SQLiteDatabase(db_path).connect().bootstrap_schema()

    events = EventStore(SQLiteDatabase(db_path).connect())
    first_id = events.append(
        {"stage": "decompose", "status": "completed", "run_id": "r1", "summary": "plan"}
    )
    second_id = events.append(
        {"stage": "synthesize", "status": "completed", "run_id": "r1", "summary": "draft"}
    )
    assert second_id > first_id

    reopened = EventStore(SQLiteDatabase(db_path).connect())
    rows = reopened.list(run_id="r1")
    assert [row["stage"] for row in rows] == ["decompose", "synthesize"]
    incremental = reopened.list(run_id="r1", after_id=first_id)
    assert [row["stage"] for row in incremental] == ["synthesize"]


def test_approval_store_create_update_reopen(tmp_path: Path) -> None:
    db_path = database_path(tmp_path)
    SQLiteDatabase(db_path).connect().bootstrap_schema()
    approvals = ApprovalStore(SQLiteDatabase(db_path).connect())
    request = ApprovalRequest(
        operation="project.plan.write",
        diff={"section": "M3"},
        risk="medium",
        input_hash="abc",
    )
    created = approvals.create(request, run_id="run-1")
    approval_id = created["approval_id"]
    assert approvals.update_result(approval_id, "approved") is True

    reopened = ApprovalStore(SQLiteDatabase(db_path).connect())
    restored = reopened.get(approval_id)
    assert restored["result"] == "approved"
    assert restored["diff"] == {"section": "M3"}
    assert [item["operation"] for item in reopened.list(result="approved")] == ["project.plan.write"]


def test_artifact_store_register_and_query(tmp_path: Path) -> None:
    db_path = database_path(tmp_path)
    SQLiteDatabase(db_path).connect().bootstrap_schema()
    artifacts = ArtifactStore(SQLiteDatabase(db_path).connect())
    ref = ArtifactRef(
        id="art-1",
        type="text/markdown",
        hash="deadbeef",
        location="objects/art-1.md",
        source_run_id="run-1",
        source_step_id="step-1",
    )
    artifacts.register(ref)

    reopened = ArtifactStore(SQLiteDatabase(db_path).connect())
    restored = reopened.get("art-1")
    assert restored["content_hash"] == "deadbeef"
    assert [item["artifact_id"] for item in reopened.list(run_id="run-1")] == ["art-1"]


def test_doctor_reports_missing_db_and_ok_after_init(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert doctor_command(str(tmp_path)) == 1
    assert "database missing" in capsys.readouterr().out
    assert init_command(str(tmp_path)) == 0
    assert doctor_command(str(tmp_path)) == 0
    assert "OK" in capsys.readouterr().out


def test_doctor_is_read_only_for_outdated_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    init_command(str(tmp_path))
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    db.connection.execute(
        "DELETE FROM schema_migrations WHERE version != ?", (SCHEMA_MIGRATIONS[0][0],)
    )
    db.connection.commit()
    db.close()

    assert doctor_command(str(tmp_path)) == 1

    reopened = SQLiteDatabase(database_path(tmp_path)).connect()
    assert reopened.schema_version() == 1
    reopened.close()
    assert "pending migrations" in capsys.readouterr().out


def test_schema_bootstrap_is_idempotent(tmp_path: Path) -> None:
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    db.bootstrap_schema()
    db.bootstrap_schema()
    assert db.schema_version() == len(SCHEMA_MIGRATIONS)
    assert db.pending_migrations() == []
    db.close()
