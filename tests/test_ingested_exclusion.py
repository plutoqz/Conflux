"""P2.6 ingested-paper exclusion — globally-ingested papers (cross-profile)
are excluded from radar candidates unless skip_ingested is disabled."""

from __future__ import annotations

from pathlib import Path

from conflux.adapters.sqlite_store import (
    PaperStore,
    SQLiteDatabase,
    list_ingested_paper_keys,
)
from conflux.core.p2_contracts import PaperIdentity, PaperSource, QuerySpec
from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_radar.radar import _paper_record_key, run_paper_radar
from conflux.project_registry.models import ProjectDefinition
from conflux.research_profile import load_profile


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    db.bootstrap_schema()
    return db


def test_list_ingested_paper_keys(tmp_path: Path) -> None:
    db = _db(tmp_path)
    store = PaperStore(db)
    store.upsert(PaperIdentity(source="arxiv", canonical_id="2405.12345"))
    store.upsert(PaperIdentity(source="semantic_scholar", canonical_id="abc123", doi="10.1000/xyz"))
    keys = list_ingested_paper_keys(db)
    assert "arxiv:2405.12345" in keys
    assert "doi:10.1000/xyz" in keys


def test_paper_record_key_matches_store_key() -> None:
    arxiv = PaperRecord(id="2401.00001", title="T", abstract="A", source="arxiv")
    assert _paper_record_key(arxiv) == "arxiv:2401.00001"
    doi = PaperRecord(id="s2-1", title="T", abstract="A", source="semantic_scholar", doi="10.1/abc")
    assert _paper_record_key(doi) == "doi:10.1/abc"


def test_cross_source_dedup_merges_arxiv_and_s2(monkeypatch, tmp_path: Path) -> None:
    """arXiv + S2 copies of the same paper are merged into one candidate.

    S2 results carry ``metadata["arxiv_id"]`` from externalIds.ArXiv; the
    canonicalization converts them to arxiv records so de-dup lands on one
    key (arxiv:...).  Ingested exclusion then also matches the arxiv key.
    """
    db = _db(tmp_path)

    def fake_arxiv(query, *, max_results=10, start=0, categories=None, sort_by="submittedDate"):
        return [PaperRecord(id="2401.00010", title="Shared paper", abstract="gis agent", source="arxiv")]

    def fake_s2(query, **kwargs):
        return [PaperRecord(
            id="s2-x1",
            title="Shared paper (from S2)",
            abstract="gis agent",
            source="semantic_scholar",
            metadata={"arxiv_id": "2401.00010", "citation_count": 30},
        )]

    monkeypatch.setattr("conflux.paper_ingestion.arxiv_source.search_arxiv", fake_arxiv)
    monkeypatch.setattr(
        "conflux.paper_ingestion.semantic_scholar_source.search_semantic_scholar",
        fake_s2,
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "GIS agents for geospatial workflows"
    proj.research = {"profile": "profiles/example_gis_agent.yaml"}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    result = run_paper_radar(proj, profile, db=db)
    ids = [link.paper_identity.canonical_id for link in result.links]
    # Both sources fed the same paper; only one link (arxiv id).
    assert ids.count("2401.00010") == 1
    assert "s2-x1" not in [str(l.paper_identity.source) + ":" + l.paper_identity.canonical_id
                            for l in result.links if "s2-x1" in str(l.paper_identity)]


def test_ingested_exclusion_matches_arxiv_id_on_s2_record(monkeypatch, tmp_path: Path) -> None:
    """An ingested arxiv paper arrives as an S2 record with the arxiv external
    id; per-spec exclusion must still drop it (canonicalized to 'arxiv:<id>')."""
    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2401.00010"))

    def fake_arxiv(query, *, max_results=10, start=0, categories=None, sort_by="submittedDate"):
        return []

    def fake_s2(query, **kwargs):
        return [PaperRecord(
            id="s2-x9",
            title="Already ingested via arXiv",
            abstract="gis",
            source="semantic_scholar",
            metadata={"arxiv_id": "2401.00010", "citation_count": 5},
        )]

    monkeypatch.setattr("conflux.paper_ingestion.arxiv_source.search_arxiv", fake_arxiv)
    monkeypatch.setattr(
        "conflux.paper_ingestion.semantic_scholar_source.search_semantic_scholar",
        fake_s2,
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml"}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    result = run_paper_radar(proj, profile, db=db)
    assert result.stats.excluded_ingested == 1
    assert all(
        l.paper_identity.canonical_id != "2401.00010"
        for l in result.links
    )


def test_run_excludes_ingested_papers(monkeypatch, tmp_path: Path) -> None:
    """A paper already in the global papers table is dropped from candidates."""
    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2401.00001"))
    # Real source calls are replaced with one ingested + one new paper.
    def fake_arxiv(query, *, max_results=10, start=0, categories=None, sort_by="submittedDate"):
        return [
            PaperRecord(id="2401.00001", title="Ingested GIS paper", abstract="gis agent", source="arxiv"),
            PaperRecord(id="2401.00002", title="New GIS paper", abstract="geospatial agent", source="arxiv"),
        ]

    monkeypatch.setattr("conflux.paper_ingestion.arxiv_source.search_arxiv", fake_arxiv)
    monkeypatch.setattr(
        "conflux.paper_ingestion.semantic_scholar_source.search_semantic_scholar",
        lambda query, **kwargs: [],
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "GIS agents for geospatial workflows"
    proj.research = {"profile": "profiles/example_gis_agent.yaml"}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    result = run_paper_radar(proj, profile, db=db)
    ids = [link.paper_identity.canonical_id for link in result.links]
    assert "2401.00002" in ids
    assert "2401.00001" not in ids
    assert result.stats.excluded_ingested == 1


def test_skip_ingested_disabled_keeps_papers(monkeypatch, tmp_path: Path) -> None:
    """When skip_ingested is disabled the exclusion filter is not applied.

    The switch is carried per-spec: override the profile tracks' expanded
    specs' ``skip_ingested`` to False before the run, and the already-ingested
    paper stays in the candidate pool.
    """
    from conflux.paper_radar.query_builder import resolve_query_specs_from_profile

    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2401.00001"))

    def fake_arxiv(query, *, max_results=10, start=0, categories=None, sort_by="submittedDate"):
        return [PaperRecord(id="2401.00001", title="Ingested GIS paper", abstract="gis agent", source="arxiv")]

    monkeypatch.setattr("conflux.paper_ingestion.arxiv_source.search_arxiv", fake_arxiv)
    monkeypatch.setattr(
        "conflux.paper_ingestion.semantic_scholar_source.search_semantic_scholar",
        lambda query, **kwargs: [],
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml"}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    # Default skip_ingested=True -> excluded.
    result = run_paper_radar(proj, profile, db=db, force_refresh=True)
    assert result.stats.excluded_ingested == 1
    assert "2401.00001" not in [l.paper_identity.canonical_id for l in result.links]

    # skip_ingested=False on all specs -> ingested paper is kept (exempt).
    proj2 = ProjectDefinition(id="test2", name="Test2", path=".")
    proj2.plan.overall_goal = "GIS agents"
    proj2.research = {"profile": "profiles/example_gis_agent.yaml"}
    specs = resolve_query_specs_from_profile(profile, config=None)
    for spec in specs:
        spec.skip_ingested = False
    result2 = run_paper_radar(
        proj2, profile, db=db, force_refresh=True, query_specs=specs,
    )
    assert result2.stats.excluded_ingested == 0
    assert "2401.00001" in [l.paper_identity.canonical_id for l in result2.links]
