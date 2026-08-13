"""P3.4 link materialization tests — runs/claims/papers/branch <-> work items.

All producers are deterministic and offline; the assertions mirror the plan
acceptance: every link carries its source identity, and cross-feature
failures never produce a wrong completion state.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from conflux.adapters.sqlite_store import RunStore, SQLiteDatabase, SearchIntentStore, ProjectPaperStore
from conflux.projects import (
    EventKind,
    ProjectIntelligence,
    ResearchWorkItem,
    build_snapshot,
    intent_work_item_map,
    materialize_links,
    new_event,
    persist_links,
    seed_reviews,
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
    project = ProjectDefinition(id="p34", name="P3.4", path=".")
    project.plan.overall_goal = "Link work items across features"
    from conflux.project_registry.models import Milestone

    project.plan.milestones = [
        Milestone(id="m-alpha", title="Alpha baseline", status="in_progress",
                  deliverables=["run-table.csv"]),
        Milestone(id="m-beta", title="Beta ablations", status="completed"),
    ]
    project.plan.next_actions = ["write report"]
    return project


def _work_item(db: SQLiteDatabase, project_id: str, work_item_id: str) -> ResearchWorkItem:
    return ProjectIntelligence(db).work_items.get(work_item_id)


# ── intent -> work item mapping ───────────────────────────────────────


def test_intent_work_item_map_matches_milestone_ids_and_titles(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    store = SearchIntentStore(db)
    store.upsert({
        "intent_id": "i-1",
        "project_id": project.id,
        "type": "milestone",
        "summary": "Alpha evidence",
        "query_terms": ["alpha"],
        "expected_evidence_types": ["metric"],
        "related_milestone_ids": ["m-alpha"],
        "source_refs": [],
        "priority": 5,
        "context_version": "v1",
        "status": "active",
    })
    store.upsert({
        "intent_id": "i-2",
        "project_id": project.id,
        "type": "evidence_gap",
        "summary": "Beta gap",
        "query_terms": ["beta"],
        "expected_evidence_types": [],
        "related_milestone_ids": [],
        "source_refs": ["milestone: Beta ablations"],
        "priority": 4,
        "context_version": "v1",
        "status": "active",
    })

    mapping = intent_work_item_map(intelligence, project)

    assert mapping[f"{project.id}:wi:ms-0"] == ["i-1"]
    assert mapping[f"{project.id}:wi:ms-1"] == ["i-2"]
    db.close()


# ── query runs + ledger claims -> links/evidence ───────────────────────


def _persist_run_with_claims(
    db: SQLiteDatabase,
    project_id: str,
    run_id: str,
    work_item_id: str,
    verdict: str = "supports",
) -> None:
    RunStore(db).create_run(
        run_id=run_id,
        status="completed",
        metadata={"project_id": project_id, "work_item_id": work_item_id,
                  "budget_consumed": {"input_tokens": 120, "output_tokens": 80}},
    )
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
    from conflux.research_protocol import ClaimRecord, EvidenceRecord, LedgerSnapshot

    repository = EvidenceLedgerRepository(db)
    snapshot = LedgerSnapshot(
        snapshot_id=f"{run_id}:snapshot-1",
        run_id=run_id,
        round="round-0",
        records=(EvidenceRecord(
            evidence_id=f"{run_id}:ev-0001",
            subquestion_id="sq-1",
            query_id=f"{run_id}:query-1",
            source_identity="https://example.test/source",
            publisher="Example",
            content_hash="hash-v1",
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
    repository.persist_run(snapshot, [ClaimRecord(
        claim_id=f"{run_id}:claim-01",
        subquestion_id="sq-1",
        text="Alpha runs reproduce.",
        claim_type="direct_fact",
        importance="critical",
        evidence_ids=[f"{run_id}:ev-0001"],
        derivation_type="direct_evidence",
        derivation_inputs=[f"{run_id}:ev-0001"],
        verification_result={"verdict": verdict, "confidence": 0.9,
                             "reason": "direct", "verifier_version": "fixture-v1"},
    )])


def test_materialize_links_query_run_and_claims(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    work_item_id = f"{project.id}:wi:ms-0"

    _persist_run_with_claims(db, project.id, "run-a", work_item_id)

    links = materialize_links(intelligence, project)

    assert links[work_item_id]["linked_run_ids"] == ["run-a"]
    evidence = links[work_item_id]["evidence_refs"]
    assert len(evidence) == 1
    assert evidence[0].startswith("claim:run-a:claim-01:supports:")
    db.close()


def test_observed_status_rules_never_invent_completion(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    # completed without evidence -> needs_review (not completed)
    items = persist_links(intelligence, project)
    beta = next(item for item in items if item["work_item_id"] == f"{project.id}:wi:ms-1")
    assert beta["declared_status"] == "completed"
    assert beta["observed_status"] == "no_evidence"
    assert beta["inferred_status"] == "needs_review"

    # completed with supporting evidence -> verified
    _persist_run_with_claims(db, project.id, "run-b", f"{project.id}:wi:ms-1")
    items = persist_links(intelligence, project)
    beta = next(item for item in items if item["work_item_id"] == f"{project.id}:wi:ms-1")
    assert beta["observed_status"] == "verified"
    assert beta["inferred_status"] == "completed"
    db.close()


def test_contradicting_evidence_flags_work_item(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    work_item_id = f"{project.id}:wi:ms-0"

    _persist_run_with_claims(db, project.id, "run-c", work_item_id, verdict="contradicts")

    items = persist_links(intelligence, project)
    alpha = next(item for item in items if item["work_item_id"] == work_item_id)
    assert alpha["observed_status"] == "failed"
    assert alpha["inferred_status"] == "needs_review"
    db.close()


# ── review producers ──────────────────────────────────────────────────


def test_seed_reviews_status_suggestion_for_completed_without_evidence(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    seed_reviews(intelligence, project)
    pending = intelligence.reviews.list(project.id, status="pending")

    kinds = {review.kind.value for review in pending}
    assert "status_suggestion" in kinds
    suggestion = next(review for review in pending if review.kind.value == "status_suggestion")
    assert f"{project.id}:wi:ms-1" in suggestion.impact_refs  # completed, no evidence
    db.close()


def test_branch_suggestion_and_divergence_reviews(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    work_item_id = f"{project.id}:wi:ms-0"

    intelligence.events.append(new_event(
        project.id, EventKind.GIT_HEAD_CHANGED,
        payload={"branch": "feature/alpha", "head": "abc", "root": ".",
                 "recent_subjects": ["wip alpha baseline"], "checked_at": time.time()},
        dedup_key="git-1",
    ))
    from conflux.projects import build_snapshot

    build_snapshot(intelligence, project)
    seed_reviews(intelligence, project)
    pending = intelligence.reviews.list(project.id, status="pending")
    suggests = [r for r in pending if r.kind.value == "branch_divergence"]
    assert any(work_item_id in (r.impact_refs or []) for r in suggests)

    # Confirm the suggestion -> linked_branch persisted on the store row.
    suggestion = next(r for r in suggests if work_item_id in (r.impact_refs or []))
    intelligence.reviews.resolve(suggestion.review_id, "confirmed")
    item = _work_item(db, project.id, work_item_id)
    item.linked_branch = "feature/alpha"
    intelligence.work_items.upsert(item)
    links = materialize_links(intelligence, project)
    assert links[work_item_id]["linked_branch"] == "feature/alpha"
    db.close()


# ── collectors: fixed latent bugs ─────────────────────────────────────


def test_collect_run_events_reads_run_store_metadata(tmp_path: Path):
    from conflux.projects.collectors import collect_run_events

    db = _db(tmp_path)
    project = _project()
    RunStore(db).create_run(
        run_id="run-x",
        status="completed",
        metadata={"project_id": project.id, "work_item_id": f"{project.id}:wi:ms-0",
                  "budget_consumed": {"input_tokens": 10, "output_tokens": 5, "elapsed_ms": 1000}},
    )
    RunStore(db).create_run(run_id="run-other", status="completed",
                            metadata={"project_id": "elsewhere"})

    events = collect_run_events(project, db)

    assert [event.payload["run_id"] for event in events] == ["run-x"]
    assert events[0].payload["work_item_id"] == f"{project.id}:wi:ms-0"
    assert events[0].payload["tokens"] == {"input": 10, "output": 5}
    db.close()


def test_collect_evidence_events_uses_source_snapshots(tmp_path: Path):
    from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
    from conflux.projects.collectors import collect_evidence_events
    from conflux.research_protocol import ClaimRecord, EvidenceRecord, LedgerSnapshot

    db = _db(tmp_path)
    project = _project()
    repository = EvidenceLedgerRepository(db)
    repository.persist_run(
        LedgerSnapshot(
            snapshot_id="src-run:snapshot-1", run_id="src-run", round="round-0",
            records=(EvidenceRecord(
                evidence_id="src-run:ev-0001", subquestion_id="sq-1", query_id="q-1",
                source_identity="https://example.test/s", publisher="P",
                content_hash="hash-1", source_type="Web", claim="fact",
                verbatim_quote="quote", evidence_class="authoritative_document",
                url="https://example.test/s", document_title="t",
                relationship="supports", subquestion_ids=["sq-1"],
            ),),
            source_statuses=(("sq-1:Web:primary", {"status": "success"}),),
        ),
        [ClaimRecord(
            claim_id="src-run:claim-01", subquestion_id="sq-1", text="fact",
            claim_type="direct_fact", importance="medium",
            evidence_ids=["src-run:ev-0001"], derivation_type="direct_evidence",
            derivation_inputs=["src-run:ev-0001"],
            verification_result={"verdict": "supports", "confidence": 0.8,
                                 "reason": "r", "verifier_version": "v1"},
        )],
    )

    events = collect_evidence_events(project, db)

    assert events, "evidence collector must find ledger snapshots"
    assert events[0].kind == EventKind.EVIDENCE_SOURCE_CHANGED
    assert events[0].payload["source_id"] == "https://example.test/s"
    assert events[0].payload["content_hash"] == "hash-1"
    # idempotent dedup: second run with same (source, hash) adds nothing new
    again = collect_evidence_events(project, db)
    assert len(again) == len(events)
    db.close()


# ── paper links ───────────────────────────────────────────────────────


def test_paper_links_by_matched_milestone_ids(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    ProjectPaperStore(db).upsert({
        "project_id": project.id,
        "paper_identity": {"source": "arxiv", "canonical_id": "alpha"},
        "status": "saved",
        "matched_intent_ids": [],
        "matched_milestone_ids": ["m-alpha"],
    })

    links = materialize_links(intelligence, project)

    assert links[f"{project.id}:wi:ms-0"]["linked_paper_keys"] == ["arxiv:alpha"]
    assert links[f"{project.id}:wi:ms-1"]["linked_paper_keys"] == []
    db.close()


# ── RAG coverage + index_stale (P3.4b) ────────────────────────────────


class _FakeVectorStore:
    name = "conflux_docs"

    def __init__(self, metadatas: list[dict]):
        self._metadatas = metadatas
        self._collection = type(
            "Collection", (),
            {"metadata": {"conflux_embedding_model": "text-embedding-3-small"}},
        )()

    def get(self, include=None, limit=5000, offset=0):
        metadatas = self._metadatas[offset:offset + limit]
        return {"metadatas": metadatas, "ids": [str(i) for i in range(len(metadatas))]}


def test_compute_coverage_marks_indexed_stale_missing(tmp_path: Path, monkeypatch):
    import conflux.rag.indexer as indexer

    from conflux.projects import ProjectDocument, compute_coverage

    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    for path, content_hash in (
        ("docs/PLAN.md", "hash-new"),
        ("README.md", "hash-same"),
        ("notes/other.md", "hash-x"),
    ):
        intelligence.documents.upsert(ProjectDocument(
            document_id=f"doc-{path}", project_id=project.id, path=path,
            content_hash=content_hash,
        ))

    monkeypatch.setattr(indexer, "create_vector_store", lambda: _FakeVectorStore([
        {"source": "project:p34:docs/PLAN.md", "doc_content_hash": "hash-old"},
        {"source": "project:p34:README.md", "doc_content_hash": "hash-same"},
    ]))

    coverage = compute_coverage(intelligence, project)

    assert coverage["indexed"] == 1
    assert coverage["stale"] == 1
    assert coverage["missing"] == 1
    assert coverage["by_document"]["docs/PLAN.md"] == "stale"
    assert coverage["by_document"]["README.md"] == "indexed"
    assert coverage["by_document"]["notes/other.md"] == "missing"
    assert coverage["model"] == "text-embedding-3-small"
    db.close()


def test_index_stale_reviews_from_coverage(tmp_path: Path, monkeypatch):
    import conflux.rag.indexer as indexer

    from conflux.projects import ProjectDocument, compute_coverage

    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()
    intelligence.documents.upsert(ProjectDocument(
        document_id="doc-plan", project_id=project.id, path="docs/PLAN.md",
        content_hash="hash-new",
    ))

    monkeypatch.setattr(indexer, "create_vector_store", lambda: _FakeVectorStore([
        {"source": "project:p34:docs/PLAN.md", "doc_content_hash": "hash-old"},
    ]))
    coverage = compute_coverage(intelligence, project)
    seed_reviews(intelligence, project, rag=coverage)

    pending = intelligence.reviews.list(project.id, status="pending")
    index_stale = [r for r in pending if r.kind.value == "index_stale"]
    assert index_stale, "stale indexed doc must produce an index_stale review"
    assert index_stale[0].impact_refs == ["doc-plan"]
    db.close()


def test_index_project_documents_chunks_with_project_metadata(tmp_path: Path, monkeypatch):
    import conflux.rag.indexer as indexer

    from conflux.projects import ProjectDocument, index_project_documents

    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Hello project\n\nBody text.\n", encoding="utf-8")
    project = ProjectDefinition(id="p34", name="P3.4", path=str(project_dir))

    intelligence.documents.upsert(ProjectDocument(
        document_id="doc-readme", project_id=project.id, path="README.md",
        content_hash="file-hash-1",
    ))
    intelligence.documents.set_authority("doc-readme", "confirmed")

    captured = {}
    captured["store"] = _FakeVectorStore([])

    def fake_index(store, documents):
        captured["documents"] = documents
        return len(documents)

    monkeypatch.setattr(indexer, "create_vector_store", lambda: captured["store"])
    monkeypatch.setattr(indexer, "index_documents", fake_index)

    result = index_project_documents(intelligence, project)

    assert result["ok"] is True
    docs = captured["documents"]
    assert docs, "confirmed docs must be chunked"
    assert all(doc.metadata["source"] == "project:p34:README.md" for doc in docs)
    assert all(doc.metadata["doc_content_hash"] == "file-hash-1" for doc in docs)
    assert any(doc.metadata.get("chunk_type") == "parent" for doc in docs)
    db.close()


def test_index_project_documents_skips_unconfirmed(tmp_path: Path, monkeypatch):
    import conflux.rag.indexer as indexer

    from conflux.projects import ProjectDocument, index_project_documents

    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Hello\n", encoding="utf-8")
    project = ProjectDefinition(id="p34", name="P3.4", path=str(project_dir))

    intelligence.documents.upsert(ProjectDocument(
        document_id="doc-readme", project_id=project.id, path="README.md",
        content_hash="file-hash-1",
    ))  # authority stays candidate

    monkeypatch.setattr(indexer, "create_vector_store", lambda: _FakeVectorStore([]))
    result = index_project_documents(intelligence, project)

    assert result["ok"] is False  # nothing to index — discovery never grants authority
    db.close()


# ── closure: gap -> evidence -> review supersede (P3.4c) ──────────────


def test_status_suggestion_superseded_once_evidence_lands(tmp_path: Path):
    db = _db(tmp_path)
    intelligence = _intelligence(db)
    project = _project()

    # Completed milestone without evidence -> suggestion appears.
    seed_reviews(intelligence, project)
    pending = intelligence.reviews.list(project.id, status="pending")
    no_evidence = [r for r in pending if r.kind.value == "status_suggestion"
                   and "没有关联证据" in r.summary]
    assert no_evidence

    # Evidence arrives (supporting claim through a run) -> superseded.
    _persist_run_with_claims(db, project.id, "run-d", f"{project.id}:wi:ms-1")
    seed_reviews(intelligence, project)
    pending = intelligence.reviews.list(project.id, status="pending")
    no_evidence = [r for r in pending if r.kind.value == "status_suggestion"
                   and "没有关联证据" in r.summary
                   and f"{project.id}:wi:ms-1" in (r.impact_refs or [])]
    assert not no_evidence, "completed-with-evidence must no longer suggest no-evidence"
    db.close()
