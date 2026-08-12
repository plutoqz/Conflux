"""P3.2 document discovery — D0/D1/D2, incremental scanning, events, and
authority confirmation (offline, no model)."""

from __future__ import annotations

from pathlib import Path

from conflux.adapters.sqlite_store import SQLiteDatabase
from conflux.projects import ProjectIntelligence, EventKind
from conflux.projects.discovery import (
    classify_document,
    discover_candidates,
    document_id_for,
    parse_document,
)
from conflux.projects.discovery_service import (
    document_map,
    get_cursor,
    scan_project_documents,
    set_cursor,
)
from conflux.projects.contracts import (
    ClassificationSource,
    DocumentAuthority,
    DocumentKind,
    ParseStatus,
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


def _project(root: Path) -> ProjectDefinition:
    return ProjectDefinition(id="p3-doc", name="Doc Test", path=str(root))


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ── D0 discovery ─────────────────────────────────────────────────


def test_discover_candidates_skips_ignored_and_unsupported(tmp_path: Path):
    root = tmp_path / "proj"
    _write(root, "docs/PLAN.md", "# Plan\n- milestone")
    _write(root, "docs/notes.txt", "notes")
    _write(root, "README.md", "# Readme")
    _write(root, "main.py", "print('x')")            # unsupported ext
    _write(root, ".git/config", "x")                  # ignored dir
    _write(root, "venv/lib.py", "x")                  # ignored dir
    _write(root, "docs/big.pdf", "x" * 5_000_000)     # oversized
    project = _project(root)

    candidates = discover_candidates(project)
    paths = {c["relative_path"] for c in candidates}
    assert "docs/PLAN.md" in paths
    assert "docs/notes.txt" in paths
    assert "README.md" in paths
    assert "main.py" not in paths
    assert ".git/config" not in paths
    assert "venv/lib.py" not in paths
    assert "docs/big.pdf" not in paths
    # README (root doc) outranks docs.
    assert candidates[0]["relative_path"] == "README.md"


# ── D1 parsing ──────────────────────────────────────────────────


def test_parse_markdown_extracts_title_and_headings(tmp_path: Path):
    path = _write(tmp_path, "docs/PLAN.md", "# GIS 研究计划\n\n## 里程碑 1\n\n正文")
    doc = parse_document(path)
    assert doc.parse_status == ParseStatus.READY
    assert doc.content_hash
    assert doc.language == "zh"
    assert "GIS 研究计划" in doc.title
    assert any("里程碑" in h for h in doc.metadata["headings"])
    assert doc.extractor_version


def test_parse_notebook_and_pdf(tmp_path: Path):
    nb = tmp_path / "nb.ipynb"
    nb.write_text(
        '{"cells": [{"cell_type": "markdown", "source": ["# Exp"]},'
        '{"cell_type": "code", "source": ["x = 1"]}], "metadata": {}}',
        encoding="utf-8",
    )
    doc = parse_document(nb)
    assert doc.parse_status == ParseStatus.READY
    assert "Exp" in doc.metadata["headings"][0]

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    pdf_doc = parse_document(pdf)
    # Fake PDF may fail extraction but must not crash and stays failed/partial.
    assert pdf_doc.parse_status in (ParseStatus.READY, ParseStatus.PARTIAL, ParseStatus.FAILED)
    assert pdf_doc.extractor_version


# ── D2 classification ───────────────────────────────────────────


def test_classify_rules_kinds_and_never_authority():
    doc = parse_document(Path("/x/docs/PLAN.md"))
    doc.path = "docs/PLAN.md"
    classify_document(doc)
    assert doc.kind == DocumentKind.PLAN
    assert doc.classification_source == ClassificationSource.RULE
    assert doc.authority == DocumentAuthority.CANDIDATE  # rules never confirm

    doc2 = parse_document(Path("/x/papers/note.md"))
    doc2.path = "papers/note.md"
    classify_document(doc2)
    assert doc2.kind == DocumentKind.PAPER_NOTE

    doc3 = parse_document(Path("/x/reports/summary.md"))
    doc3.path = "reports/summary.md"
    classify_document(doc3)
    assert doc3.kind == DocumentKind.REPORT


# ── Incremental scan ────────────────────────────────────────────


def test_scan_discovers_and_emits_events(tmp_path: Path):
    root = tmp_path / "proj"
    _write(root, "docs/PLAN.md", "# Plan\n## M1")
    _write(root, "README.md", "# Readme")
    intelligence = _intelligence(_db(tmp_path))
    project = _project(root)

    result = scan_project_documents(intelligence, project)
    assert result["ok"] is True
    assert result["new"] == 2
    assert result["events"] == 2

    kinds = {e["kind"] for e in intelligence.events.list("p3-doc")}
    assert EventKind.DOCUMENT_DISCOVERED.value in kinds
    assert intelligence.documents.list("p3-doc")[0].content_hash

    # Second scan: nothing changed -> zero re-parse.
    result2 = scan_project_documents(intelligence, project)
    assert result2["parsed"] == 0
    assert result2["events"] == 0


def test_scan_detects_change_only(tmp_path: Path):
    root = tmp_path / "proj"
    path = _write(root, "docs/PLAN.md", "# Plan v1")
    intelligence = _intelligence(_db(tmp_path))
    project = _project(root)
    scan_project_documents(intelligence, project)

    path.write_text("# Plan v2", encoding="utf-8")
    result = scan_project_documents(intelligence, project)
    assert result["parsed"] == 1
    assert result["changed"] == 1
    assert result["new"] == 0
    events = intelligence.events.list("p3-doc")
    assert any(e["kind"] == EventKind.DOCUMENT_CHANGED.value for e in events)


def test_force_rescans_even_unchanged(tmp_path: Path):
    root = tmp_path / "proj"
    _write(root, "docs/PLAN.md", "# Plan")
    intelligence = _intelligence(_db(tmp_path))
    project = _project(root)
    scan_project_documents(intelligence, project)
    result = scan_project_documents(intelligence, project, force=True)
    assert result["force"] is True
    assert result["parsed"] == 1


def test_cursor_round_trip(tmp_path: Path):
    intelligence = _intelligence(_db(tmp_path))
    set_cursor(intelligence, "p3-doc", {"docs/PLAN.md": "123"})
    cursor = get_cursor(intelligence, "p3-doc")
    assert cursor is not None
    assert cursor["cursor"]["docs/PLAN.md"] == "123"


def test_document_map_groups_by_authority(tmp_path: Path):
    root = tmp_path / "proj"
    _write(root, "docs/PLAN.md", "# Plan")
    intelligence = _intelligence(_db(tmp_path))
    project = _project(root)
    scan_project_documents(intelligence, project)

    mapping = document_map(intelligence, "p3-doc")
    assert mapping["total"] == 1
    assert "candidate" in mapping["by_authority"]

    # Human confirms authority.
    doc = intelligence.documents.list("p3-doc")[0]
    assert intelligence.documents.set_authority(doc.document_id, "confirmed") is True
    mapping2 = document_map(intelligence, "p3-doc")
    assert "confirmed" in mapping2["by_authority"]


def test_document_id_stable():
    assert document_id_for("p1", "docs/PLAN.md") == document_id_for("p1", "docs/PLAN.md")
    assert document_id_for("p1", "docs/PLAN.md") != document_id_for("p2", "docs/PLAN.md")
