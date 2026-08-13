"""P3.5 cycle audit tests — snapshot comparator, confirmed summaries, legacy migration.

Acceptance mirrors the plan (P3 §P3.5):
- every real-progress claim carries evidence refs;
- file counts / document index changes are never packaged as completion;
- legacy baselines are migrated (Git head) or explicitly marked incomparable;
- confirmed summaries become the next audit's baseline and export as
  Markdown/JSON.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from conflux.adapters.sqlite_store import ProjectPaperStore, RunStore, SQLiteDatabase
from conflux.projects import (
    EventKind,
    ProjectIntelligence,
    SnapshotTrigger,
    build_cycle_audit,
    build_snapshot,
    confirm_cycle_summary,
    latest_confirmed_summary,
    new_event,
    persist_links,
)
from conflux.project_registry.models import Milestone, ProjectDefinition


# ── helpers ───────────────────────────────────────────────────────────


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    db.bootstrap_schema()
    return db


def _intelligence(db: SQLiteDatabase) -> ProjectIntelligence:
    intelligence = ProjectIntelligence(db)
    intelligence.ensure_schema()
    return intelligence


def _project() -> ProjectDefinition:
    project = ProjectDefinition(id="p35", name="P3.5", path=".")
    project.plan.overall_goal = "Audit cycles with evidence"
    project.plan.milestones = [
        Milestone(id="m-alpha", title="Alpha baseline", status="in_progress",
                  deliverables=["run-table.csv"]),
        Milestone(id="m-beta", title="Beta ablations", status="completed"),
    ]
    project.plan.next_actions = ["write report"]
    return project


def _append_event(db: SQLiteDatabase, project_id: str, kind: EventKind, payload: dict) -> None:
    ProjectIntelligence(db).events.append(new_event(project_id, kind, payload=payload))


def _advance(db: SQLiteDatabase, project: ProjectDefinition, seconds: float = 60.0) -> dict:
    """Build a snapshot at a later timestamp so period filtering sees it."""
    time.sleep(0.01)
    return build_snapshot(_intelligence(db), project, trigger=SnapshotTrigger.MANUAL).model_dump()


def _persist_run(
    db: SQLiteDatabase,
    project_id: str,
    run_id: str,
    status: str,
    *,
    work_item_id: str = "",
) -> None:
    RunStore(db).create_run(
        run_id=run_id,
        status="completed" if status != "failed" else "failed",
        metadata={"project_id": project_id, "work_item_id": work_item_id,
                  "budget_consumed": {"input_tokens": 10, "output_tokens": 5}},
    )


# ── first baseline + confirmation ─────────────────────────────────────


def test_first_audit_is_created_baseline_without_claims(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project)

    assert audit["ok"] is True
    assert audit["baseline_status"] == "created"
    assert audit["real_progress"] == []
    assert any("首次基线" in signal for signal in audit["weak_signals"])
    assert audit["confirmed"] is False
    db.close()


def test_confirm_creates_summary_which_becomes_next_baseline(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    first = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    confirmed = confirm_cycle_summary(intelligence, project, out_dir=tmp_path / "out")

    assert confirmed["ok"] is True
    assert confirmed["confirmed"] is True
    assert confirmed["baseline_status"] == "created"
    stored = latest_confirmed_summary(intelligence, project.id)
    assert stored is not None
    assert stored["current_revision"] == first.revision
    assert (tmp_path / "out" / project.id / "cycle_summary.md").exists()
    assert (tmp_path / "out" / project.id / "cycle_summary.json").exists()

    # A later audit picks the confirmed summary as its baseline.
    _append_event(db, project.id, EventKind.GIT_HEAD_CHANGED,
                  {"root": ".", "branch": "main", "head": "deadbeef",
                   "recent_subjects": ["advance"], "checked_at": time.time()})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    audit = build_cycle_audit(intelligence, project)
    assert audit["baseline_status"] == "compared"
    assert audit["baseline"]["revision"] == first.revision
    db.close()


def test_confirm_is_idempotent_for_same_pair(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    first = confirm_cycle_summary(intelligence, project)
    second = confirm_cycle_summary(intelligence, project)

    assert first["summary_id"] == second["summary_id"]
    assert latest_confirmed_summary(intelligence, project.id)["summary_id"] == first["summary_id"]
    db.close()


# ── snapshot comparison ───────────────────────────────────────────────


def test_git_head_change_is_real_progress_with_evidence(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    _append_event(db, project.id, EventKind.GIT_HEAD_CHANGED,
                  {"root": ".", "branch": "main", "head": "c0ffee" * 5,
                   "recent_subjects": ["Implement experiment"], "checked_at": time.time()})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    assert audit["baseline_status"] == "compared"
    commit_claims = [c for c in audit["real_progress"] if c["category"] == "commit"]
    assert commit_claims
    assert all(claim["evidence_refs"] for claim in commit_claims)
    assert any(ref.startswith("git:") for ref in audit["evidence_refs"])
    db.close()


def test_failed_run_becomes_failed_experiment_and_risk_not_progress(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    _append_event(db, project.id, EventKind.RESEARCH_QUERY_COMPLETED,
                  {"run_id": "run-fail", "status": "failed", "work_item_id": "",
                   "elapsed_seconds": 12.0})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    assert audit["failed_experiments"]
    assert any("研究运行失败" in risk for risk in audit["risks"])
    assert [c for c in audit["real_progress"] if c["category"] == "experiment"] == []
    assert any("run:run-fail" in ref for ref in audit["failed_experiments"][0]["evidence_refs"])
    db.close()


def test_completed_run_is_progress_and_query_change(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    _append_event(db, project.id, EventKind.RESEARCH_QUERY_COMPLETED,
                  {"run_id": "run-ok", "status": "completed", "work_item_id": "",
                   "elapsed_seconds": 30.0})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    assert any(c["category"] == "experiment" for c in audit["real_progress"])
    assert audit["query_changes"][0]["run_id"] == "run-ok"
    db.close()


def test_work_item_completion_links_acceptance_criteria_with_supporting_evidence(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    # Supporting claim lands via a completed run with a ledger verdict.
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
    from conflux.research_protocol import ClaimRecord, EvidenceRecord, LedgerSnapshot

    work_item_id = f"{project.id}:wi:ms-0"
    _persist_run(db, project.id, "run-evidence", "completed", work_item_id=work_item_id)
    repository = EvidenceLedgerRepository(db)
    repository.persist_run(LedgerSnapshot(
        snapshot_id="run-evidence:snapshot-1",
        run_id="run-evidence",
        round="round-0",
        records=(EvidenceRecord(
            evidence_id="run-evidence:ev-1",
            subquestion_id="sq-1",
            query_id="run-evidence:query-1",
            source_identity="https://example.test/s",
            publisher="Example",
            content_hash="h1",
            source_type="Web",
            claim="Fact.",
            verbatim_quote="q",
            evidence_class="authoritative_document",
            url="https://example.test/s",
            document_title="S",
            relationship="supports",
            subquestion_ids=["sq-1"],
        ),),
        source_statuses=(),
    ), [ClaimRecord(
        claim_id="run-evidence:claim-1",
        subquestion_id="sq-1",
        text="Alpha reproduces.",
        claim_type="direct_fact",
        importance="critical",
        evidence_ids=["run-evidence:ev-1"],
        derivation_type="direct_evidence",
        derivation_inputs=["run-evidence:ev-1"],
        verification_result={"verdict": "supports", "confidence": 0.9,
                             "reason": "direct", "verifier_version": "fixture"},
    )])
    project.plan.milestones[0].status = "completed"
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    item_claims = [c for c in audit["real_progress"] if c["category"] == "work_item"]
    assert item_claims
    assert item_claims[0]["acceptance_criteria"] == ["run-table.csv"]
    assert all(claim["evidence_refs"] for claim in item_claims)
    db.close()


def test_completion_without_evidence_is_risk_not_progress(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    project.plan.milestones[0].status = "completed"
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    assert [c for c in audit["real_progress"] if c["category"] == "work_item"] == []
    assert any("没有关联证据" in risk for risk in audit["risks"])
    db.close()


def test_document_count_changes_are_weak_signals_not_progress(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    _append_event(db, project.id, EventKind.DOCUMENT_CHANGED,
                  {"path": "docs/PLAN.md", "index_version": "docidx-v2"})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    assert audit["real_progress"] == []
    assert any("文档索引更新" in signal for signal in audit["weak_signals"])
    assert any("不代表完成" in signal for signal in audit["weak_signals"])
    db.close()


def test_paper_saved_in_period_is_progress_with_evidence(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    time.sleep(0.01)
    ProjectPaperStore(db).upsert({
        "project_id": project.id,
        "paper_identity": {"source": "arxiv", "canonical_id": "2401.00001",
                           "version": "v1", "doi": "", "title_hash": "h",
                           "metadata": {"title": "A saved paper"}},
        "status": "saved",
        "matched_intent_ids": [],
        "matched_track_ids": [],
        "matched_rq_ids": [],
        "matched_milestone_ids": [],
    })
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    paper_claims = [c for c in audit["real_progress"] if c["category"] == "paper"]
    assert paper_claims
    assert any("paper:" in ref for ref in paper_claims[0]["evidence_refs"])
    assert audit["paper_changes"][0]["title"] == "A saved paper"
    db.close()


def test_next_cycle_candidates_include_blocked_failed_and_reviews(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    project.plan.milestones[0].status = "blocked"
    _append_event(db, project.id, EventKind.RESEARCH_QUERY_COMPLETED,
                  {"run_id": "run-fail2", "status": "failed", "work_item_id": ""})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    kinds = {candidate["kind"] for candidate in audit["next_cycle_candidates"]}
    assert "unblock" in kinds
    assert "retry" in kinds
    db.close()


# ── legacy baseline migration / incomparability ───────────────────────


def _legacy_snapshot_file(tmp_path: Path, git_head: str) -> Path:
    out = tmp_path / "legacy"
    out.mkdir(parents=True)
    path = out / "project_snapshot.json"
    path.write_text(json.dumps({
        "project_id": "p35",
        "path": ".",
        "captured_at": "2026-08-01T00:00:00+00:00",
        "git_available": bool(git_head),
        "git_head": git_head,
        "recent_commits": [],
        "dirty_files": [],
        "test_result": {"status": "not_run"},
        "result_files": [],
        "report_files": [],
        "errors": [],
    }), encoding="utf-8")
    return out


def test_legacy_baseline_with_git_head_is_migrated_head_only(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    legacy_dir = _legacy_snapshot_file(tmp_path, "aaaa" * 10)

    audit = build_cycle_audit(intelligence, project, legacy_out_dir=legacy_dir)

    assert audit["baseline_status"] == "legacy"
    assert audit["baseline"]["revision"] == 0
    assert any("不可比较" in signal for signal in audit["weak_signals"])


def test_legacy_baseline_without_git_head_is_marked_incomparable(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    legacy_dir = _legacy_snapshot_file(tmp_path, "")

    audit = build_cycle_audit(intelligence, project, legacy_out_dir=legacy_dir)

    assert audit["baseline_status"] == "incomparable"
    assert audit["real_progress"] == []
    assert any("无法迁移" in signal for signal in audit["weak_signals"])
    db.close()


# ── markdown export ───────────────────────────────────────────────────


def test_cycle_markdown_export_lists_claims_and_evidence(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    baseline = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    _append_event(db, project.id, EventKind.GIT_HEAD_CHANGED,
                  {"root": ".", "branch": "main", "head": "feed" * 10,
                   "recent_subjects": ["step"], "checked_at": time.time()})
    build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
    audit = build_cycle_audit(intelligence, project, baseline_revision=baseline.revision)

    confirmed = confirm_cycle_summary(
        intelligence, project,
        baseline_revision=baseline.revision,
        out_dir=tmp_path / "out",
    )

    markdown = (tmp_path / "out" / project.id / "cycle_summary.md").read_text(encoding="utf-8")
    assert "# 周期摘要：p35" in markdown
    assert "## 真实进展" in markdown
    assert "证据：`" in markdown
    assert confirmed["ok"] is True
    db.close()


# ── server endpoints (v1 API) ─────────────────────────────────────────


def _open_db(db_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(db_path).connect()
    db.bootstrap_schema()
    return db


@pytest.fixture()
def p35_server(tmp_path: Path, monkeypatch):
    from conflux.workbench import server

    db_path = tmp_path / "workbench.db"

    def open_db() -> SQLiteDatabase:
        return _open_db(db_path)

    monkeypatch.setattr(server, "_research_database", open_db)
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    return server


def _write_project_yaml(tmp_path: Path) -> None:
    import yaml

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
    (project_dir / "docs").mkdir()
    (project_dir / "docs" / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    yaml_path = projects_dir / "demo.yaml"
    yaml_path.write_text(yaml.safe_dump({
        "id": "demo",
        "name": "Demo project",
        "path": "project",
        "document_dirs": ["docs"],
        "document_files": ["README.md"],
        "plan": {
            "overall_goal": "Ship a baseline",
            "milestones": [{"id": "m1", "title": "Baseline", "status": "in_progress",
                            "deliverables": ["run-table.csv"]}],
            "next_actions": ["write report"],
        },
    }, sort_keys=False), encoding="utf-8")


def test_server_audit_get_is_read_only_draft(p35_server, tmp_path):
    _write_project_yaml(tmp_path)
    p35_server.refresh_p3_project("demo", {})

    result = p35_server.build_p3_audit("demo")

    assert result["ok"] is True
    assert result["draft"]["baseline_status"] == "created"
    assert result["confirmed_latest"] is None


def test_server_audit_post_and_confirm_roundtrip(p35_server, tmp_path):
    _write_project_yaml(tmp_path)
    p35_server.refresh_p3_project("demo", {})

    run = p35_server.run_p3_audit("demo", {})
    assert run["ok"] is True
    assert run["draft"]["baseline_status"] == "created"

    confirmed = p35_server.confirm_p3_audit("demo", {})
    assert confirmed["ok"] is True
    assert confirmed["confirmed"] is True

    state = p35_server.build_p3_project_state("demo")
    assert state["audit"] is not None
    assert state["audit"]["current_revision"] == 1
    assert state["audit"]["real_progress"] == 0


def test_server_audit_legacy_snapshot_without_git_head_is_incomparable(p35_server, tmp_path):
    _write_project_yaml(tmp_path)
    p35_server.refresh_p3_project("demo", {})

    legacy_dir = tmp_path / "reports" / "workbench" / "progress" / "demo"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "project_snapshot.json").write_text(json.dumps({
        "project_id": "demo",
        "path": "project",
        "captured_at": "2026-08-01T00:00:00+00:00",
        "git_available": False,
        "git_head": "",
        "recent_commits": [],
        "dirty_files": [],
        "test_result": {"status": "not_run"},
        "result_files": [],
        "report_files": [],
        "errors": [],
    }), encoding="utf-8")

    result = p35_server.build_p3_audit("demo")

    assert result["ok"] is True
    assert result["draft"]["baseline_status"] == "incomparable"
    assert any("无法迁移" in signal for signal in result["draft"]["weak_signals"])


def test_server_audit_missing_project(p35_server):
    assert p35_server.build_p3_audit("nope")["ok"] is False
