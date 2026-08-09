"""M3 phase 3: P2 repositories, legacy import, and Workbench durable jobs."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest
import yaml

from conflux.adapters.sqlite_store import (
    JobQueue,
    ProjectPaperStore,
    SearchIntentStore,
    SearchRunStore,
    SQLiteDatabase,
    import_legacy_project_research,
)
from conflux.core.runtime_home import database_path


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(database_path(tmp_path)).connect()
    db.bootstrap_schema()
    return db


def _cache(project_id: str = "p1") -> dict:
    return {
        "project_id": project_id,
        "context": {"project_id": project_id, "project_revision": "ctx-v1"},
        "intents": [{
            "id": "intent-1",
            "project_id": project_id,
            "type": "core_topic",
            "summary": "Graph RAG evaluation",
            "status": "proposed",
        }],
        "queries": [{"id": "query-1", "source": "arxiv", "query": "graph rag evaluation"}],
        "links": [{
            "project_id": project_id,
            "paper_identity": {"source": "arxiv", "canonical_id": "2401.00001v1"},
            "status": "shortlisted",
            "matched_intent_ids": ["intent-1"],
            "evidence_utility": "method",
            "relevance": 0.91,
        }],
        "suggestions": [],
        "stats": {"run_id": "run-1", "project_id": project_id, "shortlisted": 1},
    }


def test_p2_repositories_roundtrip_and_preserve_project_status(tmp_path: Path) -> None:
    db = _db(tmp_path)
    cache = _cache()
    intents = SearchIntentStore(db)
    papers = ProjectPaperStore(db)
    runs = SearchRunStore(db)
    intents.upsert(cache["intents"][0])
    papers.upsert(cache["links"][0])
    runs.save_result(cache, job_id="job-1")
    assert papers.update_status("p1", "arxiv:2401.00001v1", "rejected") is True
    db.close()

    reopened = _db(tmp_path)
    restored = ProjectPaperStore(reopened).list("p1")
    assert restored[0]["status"] == "rejected"
    assert restored[0]["matched_intent_ids"] == ["intent-1"]
    assert SearchIntentStore(reopened).list("p1")[0]["summary"] == "Graph RAG evaluation"
    latest = SearchRunStore(reopened).latest("p1")
    assert latest is not None
    assert latest["job_id"] == "job-1"
    assert SearchRunStore(reopened).candidates("run-1")[0]["relevance"] == 0.91
    reopened.close()


def test_p2_repositories_store_enum_values_from_contract_models(tmp_path: Path) -> None:
    from conflux.core.p2_contracts import (
        PaperIdentity,
        ProjectPaperLink,
        SearchIntent,
        SearchIntentType,
    )

    db = _db(tmp_path)
    SearchIntentStore(db).upsert(SearchIntent(
        id="intent-model",
        project_id="p1",
        type=SearchIntentType.CORE_TOPIC,
        summary="Model intent",
    ))
    ProjectPaperStore(db).upsert(ProjectPaperLink(
        project_id="p1",
        paper_identity=PaperIdentity(source="arxiv", canonical_id="2402.00002"),
    ))

    assert SearchIntentStore(db).get("intent-model")["type"] == "core_topic"
    assert ProjectPaperStore(db).list("p1")[0]["status"] == "discovered"
    db.close()


def test_legacy_project_json_import_is_hash_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "legacy" / "p1" / "papers"
    source.mkdir(parents=True)
    (source / "latest.json").write_text(json.dumps(_cache(), ensure_ascii=False), encoding="utf-8")
    (source / "seen.json").write_text(json.dumps({
        "arxiv:2401.00001v1": {"status": "rejected", "at": "2026-08-09T00:00:00"}
    }), encoding="utf-8")
    db = _db(tmp_path / "home")

    first = import_legacy_project_research(db, tmp_path / "legacy")
    second = import_legacy_project_research(db, tmp_path / "legacy")

    assert first["files"] == 2
    assert first["runs"] == 1
    assert ProjectPaperStore(db).list("p1")[0]["status"] == "rejected"
    assert second["files"] == 0
    assert second["skipped"] == 2
    db.close()


def test_legacy_import_includes_historical_search_runs(tmp_path: Path) -> None:
    source = tmp_path / "legacy" / "p1" / "papers"
    source.mkdir(parents=True)
    old = _cache()
    old["stats"] = {"run_id": "run-old", "project_id": "p1"}
    latest = _cache()
    latest["stats"] = {"run_id": "run-latest", "project_id": "p1"}
    (source / "run_run-old.json").write_text(json.dumps(old), encoding="utf-8")
    (source / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
    db = _db(tmp_path / "home")

    result = import_legacy_project_research(db, tmp_path / "legacy")

    assert result["runs"] == 2
    assert SearchRunStore(db).get("run-old") is not None
    assert SearchRunStore(db).get("run-latest") is not None
    assert SearchRunStore(db).latest("p1")["run_id"] == "run-latest"
    db.close()


def test_search_run_save_is_atomic(tmp_path: Path) -> None:
    db = _db(tmp_path)
    payload = _cache()
    payload["links"] = [payload["links"][0], payload["links"][0]]

    with pytest.raises(sqlite3.IntegrityError):
        SearchRunStore(db).save_result(payload)

    assert SearchRunStore(db).get("run-1") is None
    assert ProjectPaperStore(db).list("p1") == []
    db.close()


def test_project_paper_status_update_rejects_ambiguous_canonical_id(tmp_path: Path) -> None:
    db = _db(tmp_path)
    papers = ProjectPaperStore(db)
    for source in ("arxiv", "semantic_scholar"):
        papers.upsert({
            "project_id": "p1",
            "paper_identity": {"source": source, "canonical_id": "same-id"},
        })

    assert papers.update_status("p1", "same-id", "rejected") is False
    assert papers.update_status("p1", "arxiv:same-id", "rejected") is True
    statuses = {
        item["paper_identity"]["source"]: item["status"] for item in papers.list("p1")
    }
    assert statuses == {"arxiv": "rejected", "semantic_scholar": "discovered"}
    db.close()


def test_latest_search_run_only_returns_its_intents(tmp_path: Path) -> None:
    db = _db(tmp_path)
    intents = SearchIntentStore(db)
    runs = SearchRunStore(db)
    old = _cache()
    old["intents"][0]["id"] = "intent-old"
    old["stats"]["run_id"] = "run-old"
    intents.upsert(old["intents"][0])
    runs.save_result(old)
    latest = _cache()
    latest["intents"][0]["id"] = "intent-new"
    latest["stats"]["run_id"] = "run-new"
    intents.upsert(latest["intents"][0])
    runs.save_result(latest)

    assert [item["id"] for item in runs.intents("run-new")] == ["intent-new"]
    db.close()


def test_workbench_worker_completes_job_with_persisted_result(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path))
    from conflux.workbench import server

    db = _db(tmp_path)
    queued = JobQueue(db).enqueue("paper_radar", {"project_id": "p1"}, idempotency_key="p1-once")
    db.close()
    monkeypatch.setattr(
        server,
        "_execute_project_research_radar",
        lambda payload, job_id="": {"ok": True, "project_id": payload["project_id"], "job_id": job_id},
    )

    assert server._run_one_persistent_job("test-worker") is True

    reopened = _db(tmp_path)
    restored = JobQueue(reopened).get(queued["job_id"])
    assert restored["status"] == "completed"
    assert restored["result"]["project_id"] == "p1"
    reopened.close()


def test_workbench_schedule_is_yaml_config_plus_durable_job(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "p1.yaml").write_text(yaml.safe_dump({
        "id": "p1",
        "name": "P1",
        "path": str(project_dir),
        "research": {"profile": "profiles/radar.yaml", "sources": ["arxiv"]},
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(server, "_start_persistent_worker", lambda: None)
    result = server.configure_project_research_schedule({
        "project_id": "p1", "enabled": True, "interval_minutes": 60,
    })

    assert result["ok"] is True
    assert result["schedule"]["enabled"] is True
    assert result["job"]["status"] == "pending"
    saved = yaml.safe_load((projects_dir / "p1.yaml").read_text(encoding="utf-8"))
    assert saved["research"]["schedule_enabled"] is True
    assert saved["research"]["interval_minutes"] == 60

    db = _db(tmp_path / "home")
    jobs = JobQueue(db).list(kind="paper_radar")
    assert len(jobs) == 1
    assert jobs[0]["payload"]["periodic"] is True
    db.close()


def test_schedule_validation_does_not_mutate_yaml_or_cancel_existing_job(
    tmp_path: Path, monkeypatch
) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    project_dir.mkdir(parents=True)
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    project_file = projects_dir / "p1.yaml"
    project_file.write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
    }, sort_keys=False), encoding="utf-8")
    original = project_file.read_bytes()
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    db = _db(tmp_path / "home")
    existing = JobQueue(db).enqueue(
        "paper_radar", {"project_id": "p1", "periodic": True},
        idempotency_key="existing-periodic",
    )
    db.close()

    result = server.configure_project_research_schedule({
        "project_id": "p1", "enabled": True, "interval_minutes": 60,
    })

    assert result["ok"] is False
    assert project_file.read_bytes() == original
    reopened = _db(tmp_path / "home")
    assert JobQueue(reopened).get(existing["job_id"])["status"] == "pending"
    reopened.close()


def test_schedule_yaml_write_failure_rolls_back_job_changes(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    project_file = projects_dir / "p1.yaml"
    project_file.write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
        "research": {"profile": "profiles/radar.yaml"},
    }, sort_keys=False), encoding="utf-8")
    original = project_file.read_bytes()
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    db = _db(tmp_path / "home")
    existing = JobQueue(db).enqueue(
        "paper_radar", {"project_id": "p1", "periodic": True},
        idempotency_key="existing-periodic",
    )
    db.close()
    registry = server._project_registry()
    monkeypatch.setattr(server, "_project_registry", lambda: registry)
    monkeypatch.setattr(registry, "save", lambda project: (_ for _ in ()).throw(OSError("disk full")))

    result = server.configure_project_research_schedule({
        "project_id": "p1", "enabled": True, "interval_minutes": 60,
    })

    assert result["ok"] is False
    assert project_file.read_bytes() == original
    reopened = _db(tmp_path / "home")
    jobs = JobQueue(reopened).list(kind="paper_radar")
    assert [(job["job_id"], job["status"]) for job in jobs] == [(existing["job_id"], "pending")]
    reopened.close()


def test_terminal_periodic_failure_schedules_next_cycle(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "p1.yaml").write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
        "research": {
            "profile": "profiles/radar.yaml", "schedule_enabled": True,
            "interval_minutes": 60,
        },
    }, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        server, "_execute_project_research_radar",
        lambda payload, job_id="": {"ok": False, "error": "boom"},
    )
    db = _db(tmp_path / "home")
    failed = JobQueue(db).enqueue(
        "paper_radar", {"project_id": "p1", "periodic": True},
        idempotency_key="failing-periodic", max_attempts=1,
    )
    db.close()

    assert server._run_one_persistent_job("test-worker") is True

    reopened = _db(tmp_path / "home")
    jobs = JobQueue(reopened).list(kind="paper_radar")
    assert JobQueue(reopened).get(failed["job_id"])["status"] == "failed"
    assert len([job for job in jobs if job["status"] == "pending"]) == 1
    reopened.close()


def test_expired_final_periodic_lease_schedules_next_cycle(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "p1.yaml").write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
        "research": {
            "profile": "profiles/radar.yaml", "schedule_enabled": True,
            "interval_minutes": 60,
        },
    }, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    db = _db(tmp_path / "home")
    queue = JobQueue(db, lease_seconds=0.01)
    expired = queue.enqueue(
        "paper_radar", {"project_id": "p1", "periodic": True},
        idempotency_key="expired-periodic", max_attempts=1,
    )
    assert queue.claim("dead-worker") is not None
    db.connection.execute(
        "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?",
        (time.time() - 1, expired["job_id"]),
    )
    db.connection.commit()
    db.close()

    assert server._run_one_persistent_job("replacement-worker") is True

    reopened = _db(tmp_path / "home")
    jobs = JobQueue(reopened).list(kind="paper_radar")
    assert JobQueue(reopened).get(expired["job_id"])["status"] == "failed"
    assert len([job for job in jobs if job["status"] == "pending"]) == 1
    reopened.close()


def test_schedule_metadata_does_not_change_research_context_version(
    tmp_path: Path, monkeypatch
) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "p1.yaml").write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
        "research": {"profile": "profiles/radar.yaml", "sources": ["arxiv"]},
    }, sort_keys=False), encoding="utf-8")
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)
    project = server._project_registry().get("p1")
    assert project is not None
    before = server._project_research_context_version(project, profile)
    project.research.update({
        "schedule_enabled": True,
        "interval_minutes": 60,
        "last_run_at": "2026-08-09T00:00:00Z",
        "next_run_at": "2026-08-09T01:00:00Z",
    })

    assert server._project_research_context_version(project, profile) == before


def test_persistent_worker_restarts_when_previous_thread_is_dead(monkeypatch) -> None:
    from conflux.workbench import server

    class FakeThread:
        def __init__(self, *args, **kwargs):
            self.started = False

        def is_alive(self) -> bool:
            return self.started

        def start(self) -> None:
            self.started = True

    dead = FakeThread()
    monkeypatch.setattr(server, "_persistent_worker_thread", dead)
    monkeypatch.setattr(server.threading, "Thread", FakeThread)

    server._start_persistent_worker()

    assert server._persistent_worker_thread is not dead
    assert server._persistent_worker_thread.is_alive()


def test_schedule_reconciliation_restores_one_missing_job(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    project_dir = project_root / "project"
    profile = project_dir / "profiles" / "radar.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("id: radar\nname: Radar\nkeywords: [graph]\n", encoding="utf-8")
    projects_dir = project_root / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "p1.yaml").write_text(yaml.safe_dump({
        "id": "p1", "name": "P1", "path": str(project_dir),
        "research": {
            "profile": "profiles/radar.yaml", "schedule_enabled": True,
            "interval_minutes": 60, "next_run_at": "2026-08-09T00:00:00Z",
        },
    }, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("CONFLUX_HOME", str(tmp_path / "home"))
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", project_root)

    assert server._reconcile_project_radar_schedules() == 1
    assert server._reconcile_project_radar_schedules() == 0

    db = _db(tmp_path / "home")
    jobs = JobQueue(db).list(kind="paper_radar")
    assert len(jobs) == 1
    assert jobs[0]["status"] == "pending"
    assert jobs[0]["payload"]["periodic"] is True
    db.close()
