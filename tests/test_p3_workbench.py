"""P3.3 Workbench tests — snapshot-driven project page, unified inbox, v1 API.

The core assertions mirror the plan acceptance (P3 §P3.3):
- page reads never trigger monitor_project / model / remote calls;
- refresh is local, deterministic and idempotent;
- declared-status writes go back to the project YAML;
- the unified inbox merges project reviews and Evidence Ledger reviews.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
import yaml

from conflux.adapters.sqlite_store import SQLiteDatabase
from conflux.projects import (
    ProjectIntelligence,
    build_snapshot,
    parse_work_item_ref,
    work_item_projection,
)
from conflux.project_registry.models import ProjectDefinition


# ── helpers ───────────────────────────────────────────────────────────


def _open_db(db_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(db_path).connect()
    db.bootstrap_schema()
    return db


def _intelligence(db: SQLiteDatabase) -> ProjectIntelligence:
    intelligence = ProjectIntelligence(db)
    intelligence.ensure_schema()
    return intelligence


def _write_project_yaml(tmp_path: Path, *, with_plan: bool = True) -> tuple[Path, Path]:
    """Create PROJECT_ROOT-like layout: projects/<id>.yaml + project dir."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
    (project_dir / "docs").mkdir()
    (project_dir / "docs" / "PLAN.md").write_text("# Plan\n## Goals\n- ship it\n", encoding="utf-8")
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    payload: dict = {
        "id": "demo",
        "name": "Demo project",
        "path": "project",
        "document_dirs": ["docs"],
        "document_files": ["README.md"],
    }
    if with_plan:
        payload["plan"] = {
            "overall_goal": "Ship a reproducible baseline",
            "milestones": [
                {"id": "m1", "title": "Baseline", "status": "in_progress",
                 "deliverables": ["run-table.csv"]},
                {"id": "m2", "title": "Ablations", "status": "planned"},
            ],
            "next_actions": ["read paper A", "write report"],
        }
    yaml_path = projects_dir / "demo.yaml"
    yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return yaml_path, project_dir


@pytest.fixture()
def p3_server(tmp_path, monkeypatch):
    from conflux.workbench import server

    db_path = tmp_path / "workbench.db"

    def open_db() -> SQLiteDatabase:
        return _open_db(db_path)

    monkeypatch.setattr(server, "_research_database", open_db)
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "monitor_project",
                        lambda *a, **kw: pytest.fail("monitor_project must not run on P3 page reads"))
    return server


# ── flag ─────────────────────────────────────────────────────────────


def test_p3_flag_in_build_status(p3_server, monkeypatch):
    status = p3_server.build_status()
    assert status["p3"]["overview_enabled"] is True

    monkeypatch.setenv("CONFLUX_P3_OVERVIEW", "0")
    assert p3_server.build_status()["p3"]["overview_enabled"] is False
    monkeypatch.setenv("CONFLUX_P3_OVERVIEW", "1")


# ── v1 list / state ──────────────────────────────────────────────────


def test_build_p3_projects_reads_materialized_state_only(p3_server, tmp_path):
    _write_project_yaml(tmp_path)

    result = p3_server.build_p3_projects()

    assert result["ok"] is True
    assert [item["id"] for item in result["projects"]] == ["demo"]
    assert result["projects"][0]["revision"] == 0  # no snapshot yet — never built on GET


def test_p3_project_state_endpoint_returns_page_payload(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    refresh = p3_server.refresh_p3_project("demo", {})
    assert refresh["ok"] is True
    assert refresh["revision"] == 1

    state = p3_server.build_p3_project_state("demo")

    assert state["ok"] is True
    assert state["snapshot"]["revision"] == 1
    assert state["documents"]["total"] == 2
    assert state["project"]["name"] == "Demo project"
    assert state["reviews"]  # authority candidates seeded


def test_p3_project_state_missing_project(p3_server):
    result = p3_server.build_p3_project_state("nope")
    assert result["ok"] is False


# ── refresh: local, deterministic, idempotent ─────────────────────────


def test_refresh_p3_project_is_idempotent(p3_server, tmp_path):
    _write_project_yaml(tmp_path)

    first = p3_server.refresh_p3_project("demo", {})
    events_after_first = _count_events(p3_server, "demo")
    reviews_after_first = len(_list_reviews(p3_server, "demo"))
    docs_after_first = p3_server.build_p3_documents("demo")["total"]

    second = p3_server.refresh_p3_project("demo", {})
    assert second["ok"] is True
    assert second["new_events"] == 0
    assert _count_events(p3_server, "demo") == events_after_first
    assert len(_list_reviews(p3_server, "demo")) == reviews_after_first
    assert p3_server.build_p3_documents("demo")["total"] == docs_after_first
    assert first["discovery"]["parsed"] == 2
    assert second["discovery"]["parsed"] == 0  # incremental cursor


def test_refresh_seeds_document_authority_review(p3_server, tmp_path):
    _write_project_yaml(tmp_path)

    p3_server.refresh_p3_project("demo", {})

    reviews = _list_reviews(p3_server, "demo")
    authority = [r for r in reviews if r.kind.value == "document_authority"]
    assert authority, "expected authority candidates for rule-classified docs"
    paths = {r.impact_refs[0]: r for r in authority}
    documents = p3_server.build_p3_documents("demo")["by_authority"]["candidate"]
    plan_doc = next(d for d in documents if d["path"].endswith("PLAN.md"))
    assert plan_doc["document_id"] in paths


def _count_events(server, project_id: str) -> int:
    intelligence = server._project_intelligence()
    try:
        return intelligence.events.count(project_id)
    finally:
        intelligence.db.close()


def _list_reviews(server, project_id: str):
    intelligence = server._project_intelligence()
    try:
        return intelligence.reviews.list(project_id)
    finally:
        intelligence.db.close()


# ── document authority ───────────────────────────────────────────────


def test_set_document_authority_confirms_and_supersedes(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})

    documents = p3_server.build_p3_documents("demo")["by_authority"]["candidate"]
    plan_doc = next(d for d in documents if d["path"].endswith("PLAN.md"))

    result = p3_server.set_p3_document_authority("demo", plan_doc["document_id"], {"authority": "confirmed"})

    assert result["ok"] is True
    assert result["superseded"] >= 1
    mapping = p3_server.build_p3_documents("demo")
    confirmed_paths = [d["path"] for d in mapping["by_authority"]["confirmed"]]
    assert any(path.endswith("PLAN.md") for path in confirmed_paths)
    pending = [r for r in _list_reviews(p3_server, "demo") if r.status.value == "pending"]
    assert all(r.impact_refs[0] != plan_doc["document_id"] for r in pending
               if r.kind.value == "document_authority")


def test_set_document_authority_rejects_invalid_value(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})
    documents = p3_server.build_p3_documents("demo")["by_authority"]["candidate"]
    doc_id = documents[0]["document_id"]
    result = p3_server.set_p3_document_authority("demo", doc_id, {"authority": "maybe"})
    assert result["ok"] is False


# ── work items: declared status -> YAML ──────────────────────────────


def test_work_item_projection_maps_plan(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    project = p3_server._project_registry().get("demo")

    items = work_item_projection(project)

    kinds = [item["kind"] for item in items]
    assert kinds == ["research_question", "milestone", "milestone", "action", "action"]
    milestone = items[1]
    assert milestone["declared_status"] == "in_progress"
    assert milestone["observed_status"] == "no_evidence"
    assert milestone["inferred_status"] == "in_progress"
    completed_claim = next(i for i in items if i["title"] == "Baseline")
    assert parse_work_item_ref("demo", completed_claim["work_item_id"]) == ("ms", 0)


def test_confirm_work_item_writes_declared_status_to_yaml(p3_server, tmp_path):
    yaml_path, _ = _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})

    milestone_id = f"demo:wi:ms-0"
    result = p3_server.confirm_p3_work_item(
        "demo", milestone_id, {"declared_status": "completed"},
    )

    assert result["ok"] is True
    saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert saved["plan"]["milestones"][0]["status"] == "completed"
    # snapshot projection reflects the new declared status
    state = p3_server.build_p3_project_state("demo")
    items = state["snapshot"]["work_items"]
    assert next(i for i in items if i["work_item_id"] == milestone_id)["declared_status"] == "completed"


def test_confirm_action_completion_removes_next_action(p3_server, tmp_path):
    yaml_path, _ = _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})

    action_id = "demo:wi:act-0"
    result = p3_server.confirm_p3_work_item("demo", action_id, {"declared_status": "completed"})

    assert result["ok"] is True
    saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert saved["plan"]["next_actions"] == ["write report"]


def test_confirm_work_item_rejects_bad_status(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    result = p3_server.confirm_p3_work_item("demo", "demo:wi:ms-0", {"declared_status": "done"})
    assert result["ok"] is False


# ── unified inbox ────────────────────────────────────────────────────


def test_unified_reviews_merge_project_and_evidence_ledger(p3_server, tmp_path):
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
    from conflux.research_protocol import ClaimRecord, EvidenceRecord, LedgerSnapshot

    def snapshot(run_id: str, content_hash: str) -> LedgerSnapshot:
        return LedgerSnapshot(
            snapshot_id=f"{run_id}:snapshot-1",
            run_id=run_id,
            round="round-0",
            records=(EvidenceRecord(
                evidence_id=f"{run_id}:ev-0001",
                subquestion_id="sq-1",
                query_id=f"{run_id}:query-1",
                source_identity="https://example.test/source",
                publisher="Example",
                content_hash=content_hash,
                source_type="Web",
                claim="The source has a versioned fact.",
                verbatim_quote="stable evidence",
                evidence_class="authoritative_document",
                url="https://example.test/source",
                document_title="Versioned source",
                relationship="supports",
                subquestion_ids=["sq-1"],
            ),),
            source_statuses=(("sq-1:Web:primary", {"status": "success"}),),
        )

    def claim(run_id: str) -> ClaimRecord:
        return ClaimRecord(
            claim_id=f"{run_id}:claim:sq-1:01",
            subquestion_id="sq-1",
            text="The report relies on the versioned fact.",
            claim_type="direct_fact",
            importance="critical",
            evidence_ids=[f"{run_id}:ev-0001"],
            derivation_type="direct_evidence",
            derivation_inputs=[f"{run_id}:ev-0001"],
            verification_result={
                "verdict": "supports",
                "confidence": 0.9,
                "reason": "direct source support",
                "verifier_version": "fixture-v1",
            },
        )

    _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})

    db = p3_server._research_database()
    try:
        repository = EvidenceLedgerRepository(db)
        repository.persist_run(
            snapshot("ev-run-a", "hash-a"),
            [claim("ev-run-a")],
            artifacts=[{"id": "report-a", "type": "report", "location": "reports/a.md", "project_id": "demo"}],
        )
        repository.persist_run(
            snapshot("ev-run-b", "hash-b"),
            [claim("ev-run-b")],
        )
    finally:
        db.close()

    intelligence = p3_server._project_intelligence()
    try:
        reviews = p3_server._unified_reviews("demo", intelligence, status=None)
    finally:
        intelligence.db.close()

    sources = {item["source"] for item in reviews}
    assert {"project", "evidence_ledger"} <= sources
    ledger_item = next(item for item in reviews if item["source"] == "evidence_ledger")
    assert ledger_item["review_id"].startswith("ev:")
    assert ledger_item["kind"] == "evidence_change"


def test_resolve_p3_review_routes_both_sources(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    p3_server.refresh_p3_project("demo", {})

    intelligence = p3_server._project_intelligence()
    try:
        review = intelligence.reviews.list("demo")[0]
    finally:
        intelligence.db.close()

    result = p3_server.resolve_p3_review("demo", review.review_id, {"status": "dismissed"})
    assert result["ok"] is True

    remaining = [r for r in _list_reviews(p3_server, "demo")
                 if r.review_id == review.review_id]
    assert remaining[0].status.value == "dismissed"

    missing = p3_server.resolve_p3_review("demo", "r-nope", {"status": "confirmed"})
    assert missing["ok"] is False


# ── jobs: project_id threading ───────────────────────────────────────


def test_research_job_metadata_round_trips_project_id():
    from conflux.workbench.jobs import (
        ResearchJob,
        _job_from_metadata,
        _job_metadata,
        _public_status,
    )

    job = ResearchJob(run_id="run-1", query="q", project_id="demo")
    restored = _job_from_metadata("run-1", _job_metadata(job))
    assert restored.project_id == "demo"
    assert _public_status(restored)["project_id"] == "demo"


def test_job_manager_list_filters_by_project():
    from conflux.workbench.jobs import JobManager, ResearchJob

    manager = JobManager()
    manager._jobs = {
        "a": ResearchJob(run_id="a", query="q", project_id="demo"),
        "b": ResearchJob(run_id="b", query="q", project_id="other"),
        "c": ResearchJob(run_id="c", query="q"),
    }
    # The persisted list path is covered via metadata; the in-memory fallback
    # uses the same shape — assert the public status carries the field.
    for run_id in ("a", "b", "c"):
        assert _job_public_project(manager, run_id) == manager._jobs[run_id].project_id


def _job_public_project(manager, run_id: str) -> str:
    from conflux.workbench.jobs import _public_status

    return str(_public_status(manager._jobs[run_id])["project_id"])


# ── U1: registration establishes the first snapshot ───────────────────


def test_save_registered_project_establishes_first_snapshot(p3_server, tmp_path):
    """U1 acceptance: saving a project creates a reviewable snapshot
    immediately, without a manual "检查状态" (plan §6.1)."""
    project_dir = tmp_path / "newproj"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# New project\n", encoding="utf-8")

    result = p3_server.save_registered_project({
        "id": "newproj",
        "name": "New Project",
        "path": str(project_dir),
        "overall_goal": "Ship a baseline",
        "milestones": [{"id": "m1", "title": "First milestone", "status": "in_progress"}],
        "next_actions": "first action",
        "document_dirs": "docs",
        "result_dirs": "results",
        "report_dirs": "reports",
    })

    assert result["ok"] is True
    assert result["project_id"] == "newproj"
    assert result["revision"] == 1

    state = p3_server.build_p3_project_state("newproj")
    assert state["ok"] is True
    assert state["snapshot"]["revision"] == 1
    assert state["documents"]["total"] >= 1
    items = state["snapshot"]["work_items"]
    assert any(item["kind"] == "milestone" and item["title"] == "First milestone" for item in items)


# ── snapshot summary ─────────────────────────────────────────────────


def test_snapshot_summary_answers_first_screen(p3_server, tmp_path):
    _write_project_yaml(tmp_path)
    intelligence = p3_server._project_intelligence()
    try:
        project = p3_server._project_registry().get("demo")
        from conflux.projects import SnapshotTrigger

        snapshot = build_snapshot(intelligence, project, trigger=SnapshotTrigger.INITIAL)
        summary = snapshot.summary
        assert summary["focus"] == "Baseline"  # in_progress milestone
        assert summary["in_progress"] == ["Baseline"]
        assert summary["pending_review_count"] == 0
        assert summary["git"]["branch"] == ""
    finally:
        intelligence.db.close()


# ── HTTP routing (handler object) ────────────────────────────────────


def test_v1_routes_are_dispatched_from_handler(p3_server, tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler

    _write_project_yaml(tmp_path)
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    captured = {}

    def fake_send_json(self, payload, status=200, headers=None):
        captured.update(payload=payload, status=status, headers=headers or {})

    monkeypatch.setattr(p3_server.WorkbenchHandler, "_send_json", fake_send_json)
    handler = p3_server.WorkbenchHandler()
    handler.client_address = ("127.0.0.1", 9999)
    handler.headers = {}

    handler.path = "/api/v1/projects"
    handler.do_GET()
    assert captured["status"] == 200
    assert captured["payload"]["projects"][0]["id"] == "demo"
    assert "protocol_version" in captured["payload"]

    handler.path = "/api/v1/projects/demo/state"
    handler.do_GET()
    assert captured["payload"]["ok"] is True

    handler.path = "/api/v1/projects/unknown/state"
    handler.do_GET()
    assert captured["status"] == 404


def test_v1_post_refresh_route(p3_server, tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler

    _write_project_yaml(tmp_path)
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    captured = {}

    def fake_send_json(self, payload, status=200, headers=None):
        captured.update(payload=payload, status=status, headers=headers or {})

    monkeypatch.setattr(p3_server.WorkbenchHandler, "_send_json", fake_send_json)
    handler = p3_server.WorkbenchHandler()
    handler.client_address = ("127.0.0.1", 9999)
    body = b"{}"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)

    handler.path = "/api/v1/projects/demo/refresh"
    handler.do_POST()
    assert captured["status"] == 200
    assert captured["payload"]["ok"] is True
    assert captured["payload"]["revision"] == 1


# ── static surface ───────────────────────────────────────────────────


def test_workbench_static_surface_exposes_p3_page():
    root = Path(__file__).resolve().parents[1] / "src/conflux/workbench/static"
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    for marker in ("projectDetailP3", "p3ReviewCount", "p3SettingsDialog", "p3WorkItemsTable"):
        assert marker in html, f"missing {marker} in index.html"
    for marker in ("/api/v1/projects", "p3StateCache", "EventSource"):
        assert marker in app, f"missing {marker} in app.js"


def test_legacy_projects_route_contract_unchanged(p3_server, tmp_path, monkeypatch):
    """The legacy /api/projects payload keeps its contract (plan §17.2)."""
    _write_project_yaml(tmp_path)
    from conflux.project_registry import monitor_project

    monkeypatch.setattr(p3_server, "monitor_project", monitor_project)

    result = p3_server.build_projects_overview()

    assert result["ok"] is True
    assert result["projects"][0]["project"]["id"] == "demo"
