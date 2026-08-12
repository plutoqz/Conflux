"""P2.6 citation seed expansion — seed selection, hop budget, and
ingested/seen exclusion (network mocked)."""

from __future__ import annotations

from pathlib import Path

from conflux.adapters.sqlite_store import PaperStore, SQLiteDatabase
from conflux.core.p2_contracts import PaperIdentity, ProjectResearchConfig
from conflux.paper_radar.seed_expander import (
    _s2_id_from_paper_key,
    collect_citation_seeds,
)
from conflux.research_profile import load_profile


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    db.bootstrap_schema()
    return db


def test_s2_id_from_paper_key():
    assert _s2_id_from_paper_key("arxiv:2405.12345v1") == "arXiv:2405.12345v1"
    assert _s2_id_from_paper_key("doi:10.1000/xyz") == "DOI:10.1000/xyz"
    assert _s2_id_from_paper_key("semantic_scholar:abc") is None
    assert _s2_id_from_paper_key("") is None


def test_collect_citation_seeds_expands_and_excludes(monkeypatch, tmp_path: Path):
    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2405.12345v1"))

    def fake_fetch_relations(s2_id, relation, limit):
        if s2_id == "arXiv:2405.12345v1":
            return [{
                "citedPaper" if relation == "references" else "citingPaper": {
                    "paperId": "seed-new-1",
                    "title": "New related paper",
                    "abstract": "geospatial agent verification",
                    "year": 2023,
                    "externalIds": {"ArXiv": "2401.99999"},
                    "citationCount": 42,
                }
            }]
        return []

    monkeypatch.setattr("conflux.paper_radar.seed_expander._fetch_relations", fake_fetch_relations)
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    config = ProjectResearchConfig(
        profile="profiles/example_gis_agent.yaml",
        citation_seed_enabled=True,
        citation_seed_hop=1,
        citation_seed_per_paper=5,
        citation_seed_budget=10,
    )
    records = collect_citation_seeds(db, profile=profile, config=config)
    assert len(records) == 1
    assert records[0].id == "seed-new-1"
    assert records[0].matched_queries == ["citation_seed"]


def test_collect_citation_seeds_excludes_seen(monkeypatch, tmp_path: Path):
    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2405.12345v1"))

    def fake_fetch_relations(s2_id, relation, limit):
        return [{
            "citedPaper" if relation == "references" else "citingPaper": {
                "paperId": "seen-paper",
                "title": "Already seen",
                "abstract": "x",
                "year": 2022,
                "externalIds": {"ArXiv": "2401.88888"},
                "citationCount": 1,
            }
        }]

    monkeypatch.setattr("conflux.paper_radar.seed_expander._fetch_relations", fake_fetch_relations)
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    config = ProjectResearchConfig(
        profile="profiles/example_gis_agent.yaml",
        citation_seed_enabled=True,
        citation_seed_hop=1,
        citation_seed_per_paper=5,
        citation_seed_budget=10,
    )
    # The expanded paper is already in the seen set -> excluded.
    records = collect_citation_seeds(
        db, profile=profile, config=config,
        seen_keys={"arxiv:2401.88888"},
    )
    assert records == []


def test_collect_citation_seeds_empty_without_ingested(monkeypatch, tmp_path: Path):
    """No ingested papers -> no seeds -> explicit skip signal (None)."""
    db = _db(tmp_path)  # empty papers table

    def fake_fetch_relations(s2_id, relation, limit):
        return []

    monkeypatch.setattr("conflux.paper_radar.seed_expander._fetch_relations", fake_fetch_relations)
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    config = ProjectResearchConfig(
        profile="profiles/example_gis_agent.yaml",
        citation_seed_enabled=True,
    )
    assert collect_citation_seeds(db, profile=profile, config=config) is None


def test_collect_citation_seeds_all_seen_returns_empty(monkeypatch, tmp_path: Path):
    """Seeds exist but every expandable paper is already seen -> [] (not None)."""
    db = _db(tmp_path)
    PaperStore(db).upsert(PaperIdentity(source="arxiv", canonical_id="2405.12345v1"))

    def fake_fetch_relations(s2_id, relation, limit):
        return [{
            "citedPaper" if relation == "references" else "citingPaper": {
                "paperId": "seed-old",
                "title": "Old paper",
                "abstract": "geospatial",
                "year": 2020,
                "externalIds": {"ArXiv": "2401.77777"},
                "citationCount": 3,
            }
        }]

    monkeypatch.setattr("conflux.paper_radar.seed_expander._fetch_relations", fake_fetch_relations)
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    config = ProjectResearchConfig(
        profile="profiles/example_gis_agent.yaml",
        citation_seed_enabled=True,
        citation_seed_hop=1,
        citation_seed_per_paper=5,
        citation_seed_budget=10,
    )
    # The only expandable paper is in the seen set -> still [] (seeds exist).
    records = collect_citation_seeds(
        db, profile=profile, config=config,
        seen_keys={"arxiv:2401.77777"},
    )
    assert records == []
