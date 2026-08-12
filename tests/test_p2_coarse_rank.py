"""P2 embedding coarse-rank tests: hybrid ranking, caching, no-fallback."""

from __future__ import annotations

import pytest

from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_radar.coarse_rank import embedding_coarse_rank
from conflux.research_profile import load_profile
from conflux.core.p2_contracts import ProjectResearchContext


def _paper(paper_id: str, title: str, abstract: str = "") -> PaperRecord:
    return PaperRecord(id=paper_id, title=title, abstract=abstract, source="arxiv")


def _context() -> ProjectResearchContext:
    return ProjectResearchContext(
        project_id="test",
        overall_goal="Knowledge-graph-augmented GIS agents for geospatial data fusion and workflow verification",
        research_questions=["How can agents verify geospatial processing steps?"],
    )


def test_hybrid_rank_puts_relevant_paper_first():
    from conftest import FakeEmbedding

    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    papers = [
        _paper("rel-1", "GIS agent workflow verification with knowledge graphs", "geospatial verification of agent steps"),
        _paper("off-1", "Quantum chemistry of bosonic condensates", "pure physics unrelated to agents"),
        _paper("rel-2", "Evaluating spatial reasoning agents on geospatial benchmarks", "agent evaluation and reproducibility"),
    ]
    ranked = embedding_coarse_rank(papers, profile, _context(), embedding_model=FakeEmbedding())
    top_ids = [paper.id for paper, _, _ in ranked]
    assert top_ids[0] in {"rel-1", "rel-2"}
    assert top_ids[-1] == "off-1"
    # detail is auditable
    _, combined, detail = ranked[0]
    assert detail["dense"] > detail["lexical"] or combined > 0.0


def test_embedding_cache_avoids_duplicate_requests():
    from conftest import FakeEmbedding

    class CountingEmbedding(FakeEmbedding):
        def __init__(self):
            super().__init__()
            self.embed_documents_calls = 0
            self.embed_query_calls = 0

        def embed_documents(self, texts):
            self.embed_documents_calls += 1
            return super().embed_documents(texts)

        def embed_query(self, text):
            self.embed_query_calls += 1
            return super().embed_query(text)

    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    model = CountingEmbedding()
    cache: dict = {}
    papers = [_paper("p-1", "GIS agent verification", "geospatial agent"), _paper("p-2", "other paper", "x")]
    embedding_coarse_rank(papers, profile, _context(), embedding_model=model, cache=cache)
    calls_after_first = (model.embed_documents_calls, model.embed_query_calls)
    # Second run with the same cache must not re-embed anything.
    embedding_coarse_rank(papers, profile, _context(), embedding_model=model, cache=cache)
    assert (model.embed_documents_calls, model.embed_query_calls) == calls_after_first
    assert cache




def test_multi_query_vectors_match_different_aspects():
    from conftest import FakeEmbedding
    from conflux.paper_radar.coarse_rank import _context_query_texts

    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    context = ProjectResearchContext(
        project_id="test",
        overall_goal="GIS agents for geospatial workflows",
        research_questions=[
            "How to verify geospatial processing steps?",
            "How to integrate knowledge graphs with geospatial reasoning?",
        ],
    )
    query_texts = _context_query_texts(profile, context)
    assert len(query_texts) >= 3  # goal + 2 RQs (+ keywords block)

    papers = [
        _paper("kg-1", "Knowledge graphs for geospatial reasoning", "geokg integration with agent memory"),
        _paper("verif-1", "Geospatial processing step verification", "auditing spatial agent steps"),
        _paper("off-1", "Quantum chemistry of bosons", "pure physics"),
    ]
    ranked = embedding_coarse_rank(papers, profile, context, embedding_model=FakeEmbedding())
    top_ids = [paper.id for paper, _, _ in ranked]
    assert "off-1" == top_ids[-1]
    # Both aspect-matching papers should beat the off-domain one; each matches
    # a different query vector via the max-similarity aggregation.
    assert top_ids.index("kg-1") < top_ids.index("off-1")
    assert top_ids.index("verif-1") < top_ids.index("off-1")
def test_radar_run_fails_when_embedding_unavailable(monkeypatch):
    """No silent lexical fallback: embedding failure fails the run."""
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    def boom(*args, **kwargs):
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr("conflux.paper_radar.radar.create_embedding_model", boom)
    monkeypatch.setattr(
        "conflux.paper_radar.radar._execute_queries",
        lambda queries, stats=None, db=None: (
            [PaperRecord(id="2401.00001", title="GIS agent paper", abstract="verification", source="arxiv")],
            [],
            set(),
        ),
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "Test goal"
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    with pytest.raises(RuntimeError, match="embedding provider unavailable"):
        run_paper_radar(proj, profile)
