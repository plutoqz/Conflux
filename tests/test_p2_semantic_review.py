"""P2 batch LLM semantic review tests: parsing, unreviewed semantics, rerank."""

from __future__ import annotations

import json

import pytest

from conflux.core.p2_contracts import (
    PaperLinkStatus,
    ProjectResearchContext,
    RadarRunStats,
)
from conflux.paper_radar.semantic_review import (
    batch_semantic_review,
    review_one_paper,
)
from conflux.paper_ingestion.models import PaperRecord


class _ReviewLLM:
    def __init__(self, content: str = "", *, raise_error: bool = False):
        self.content = content
        self.raise_error = raise_error
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("review model unavailable")

        class _Resp:
            content = self.content
            usage_metadata = {"total_tokens": 90}

        return _Resp()


def _context() -> ProjectResearchContext:
    return ProjectResearchContext(
        project_id="test",
        overall_goal="Knowledge-graph-augmented GIS agents",
        research_questions=["How to verify geospatial agent steps?"],
    )


def _paper_dict(paper_id: str = "2401.00001") -> dict:
    return {
        "id": paper_id,
        "title": "GIS Agent Verification with Knowledge Graphs",
        "abstract": "A framework for geospatial agent step verification.",
    }


def test_review_parses_llm_output():
    payload = {
        "relevance": 0.9,
        "research_value": 0.8,
        "evidence_quality": 0.7,
        "reasoning": "Directly addresses verification of geospatial agents.",
        "confidence": 0.85,
        "needs_deeper_review": True,
        "evidence_utility": "method",
    }
    model = _ReviewLLM(json.dumps(payload))
    review = review_one_paper(_paper_dict(), _context(), model)
    assert review.reviewed is True
    assert review.relevance == 0.9
    assert review.research_value == 0.8
    assert review.evidence_utility == "method"
    assert review.needs_deeper_review is True
    assert review.telemetry["total_tokens"] == 90


def test_review_failure_is_unreviewed():
    model = _ReviewLLM(raise_error=True)
    review = review_one_paper(_paper_dict(), _context(), model)
    assert review.reviewed is False
    assert review.telemetry["fell_back"] is True
    assert review.relevance == 0.0


def test_invalid_json_is_unreviewed():
    model = _ReviewLLM("not json at all")
    review = review_one_paper(_paper_dict(), _context(), model)
    assert review.reviewed is False
    assert review.telemetry["fell_back"] is True


def test_batch_records_stats_and_failures():
    stats = RadarRunStats(project_id="test", run_id="r")
    model = _ReviewLLM(json.dumps({"relevance": 0.8, "research_value": 0.6,
                                   "evidence_quality": 0.7, "reasoning": "x",
                                   "confidence": 0.7, "needs_deeper_review": False,
                                   "evidence_utility": "metric"}))
    reviews = batch_semantic_review(
        [_paper_dict("p-1"), _paper_dict("p-2")],
        _context(),
        model,
        max_papers=2,
        stats=stats,
    )
    assert len(reviews) == 2
    assert all(review.reviewed for review in reviews.values())
    assert stats.semantic_review_calls == 2
    assert stats.semantic_review_tokens == 180
    assert stats.semantic_review_failed == 0


def test_radar_llm_review_reranks_links(monkeypatch):
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    def mock_execute(queries, stats=None):
        return [PaperRecord(id="2401.00001", title="m", abstract="m", source="arxiv")], []

    monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
    monkeypatch.setattr(
        "conflux.paper_radar.coarse_rank.embedding_coarse_rank",
        _fake_coarse_rank({"2401.00001": 0.30}),
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "Knowledge-graph-augmented GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 0}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    model = _ReviewLLM(json.dumps({
        "relevance": 0.93, "research_value": 0.8, "evidence_quality": 0.7,
        "reasoning": "directly relevant", "confidence": 0.9,
        "needs_deeper_review": False, "evidence_utility": "method",
    }))
    result = run_paper_radar(proj, profile, llm_review=True, review_model=model)
    assert result.stats.semantic_review_count == 1
    assert result.stats.semantic_review_failed == 0
    assert result.links[0].relevance == 0.93  # LLM review relevance




def test_layered_review_only_reviews_fuzzy_band(monkeypatch):
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    def mock_execute(queries, stats=None):
        return [
            PaperRecord(id="high-1", title="h", abstract="h", source="arxiv"),
            PaperRecord(id="mid-1", title="m", abstract="m", source="arxiv"),
            PaperRecord(id="low-1", title="l", abstract="l", source="arxiv"),
        ], []

    captured = {}

    def fake_batch(papers, context, llm_model, *, max_papers, profile_keywords=None, stats=None):
        captured["ids"] = [p["id"] for p in papers]
        return {p["id"]: None for p in papers}

    monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
    monkeypatch.setattr(
        "conflux.paper_radar.coarse_rank.embedding_coarse_rank",
        _fake_coarse_rank({"high-1": 0.45, "mid-1": 0.30, "low-1": 0.15}),
    )
    monkeypatch.setattr("conflux.paper_radar.semantic_review.batch_semantic_review", fake_batch)
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "Knowledge-graph-augmented GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 0}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    run_paper_radar(
        proj,
        profile,
        llm_review=True,
        review_model=_ReviewLLM(),
        layered_review=True,
    )

    # Only the fuzzy band (0.25-0.35) is reviewed; high/low are accepted/rejected directly.
    assert captured["ids"] == ["mid-1"]


def test_non_layered_review_reviews_top_candidates(monkeypatch):
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    def mock_execute(queries, stats=None):
        return [
            PaperRecord(id="high-1", title="h", abstract="h", source="arxiv"),
            PaperRecord(id="mid-1", title="m", abstract="m", source="arxiv"),
            PaperRecord(id="low-1", title="l", abstract="l", source="arxiv"),
        ], []

    captured = {}

    def fake_batch(papers, context, llm_model, *, max_papers, profile_keywords=None, stats=None):
        captured["ids"] = [p["id"] for p in papers]
        return {p["id"]: None for p in papers}

    monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
    monkeypatch.setattr(
        "conflux.paper_radar.coarse_rank.embedding_coarse_rank",
        _fake_coarse_rank({"high-1": 0.45, "mid-1": 0.30, "low-1": 0.15}),
    )
    monkeypatch.setattr("conflux.paper_radar.semantic_review.batch_semantic_review", fake_batch)
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "Knowledge-graph-augmented GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 0}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    run_paper_radar(
        proj,
        profile,
        llm_review=True,
        review_model=_ReviewLLM(),
        layered_review=False,
    )

    # Non-layered mode reviews the top candidates by coarse score.
    assert captured["ids"] == ["high-1", "mid-1", "low-1"]


def test_radar_semantic_review_failure_marks_needs_review(monkeypatch):
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    def mock_execute(queries, stats=None):
        return [PaperRecord(id="2401.00001", title="m", abstract="m", source="arxiv")], []

    monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
    monkeypatch.setattr(
        "conflux.paper_radar.coarse_rank.embedding_coarse_rank",
        _fake_coarse_rank({"2401.00001": 0.30}),
    )
    proj = ProjectDefinition(id="test", name="Test", path=".")
    proj.plan.overall_goal = "Knowledge-graph-augmented GIS agents"
    proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 0}
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

    result = run_paper_radar(proj, profile, llm_review=True, review_model=_ReviewLLM(raise_error=True))
    assert result.stats.semantic_review_failed == 1
    assert result.links[0].status == PaperLinkStatus.NEEDS_REVIEW


def _fake_coarse_rank(combined_by_id):
    """Deterministic embedding_coarse_rank replacement for layered-review tests."""
    def fake_rank(papers, profile, context, *, embedding_model, cache=None):
        ranked = []
        for paper in papers:
            combined = combined_by_id.get(paper.id, 0.25)
            ranked.append((paper, combined, {"dense": combined, "lexical": 0.0}))
        ranked.sort(key=lambda item: -item[1])
        return ranked
    return fake_rank
