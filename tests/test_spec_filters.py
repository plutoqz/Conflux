"""P2.6 per-spec post-retrieval filters — classic tier venue + citation
floor applied in _execute_queries (unit-level, sources mocked)."""

from __future__ import annotations

from conflux.core.p2_contracts import PaperSource, QuerySpec
from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_radar.radar import _apply_spec_filters


def _paper(pid: str, *, venue: str = "", citations: int = 0) -> PaperRecord:
    return PaperRecord(
        id=pid,
        title=f"Paper {pid}",
        abstract="abstract",
        source="semantic_scholar",
        venue=venue,
        metadata={"citation_count": citations},
    )


def _spec(*, venue_filters: list[str] | None = None, min_citations: int | None = None) -> QuerySpec:
    return QuerySpec(
        id="s1",
        track_id="t1",
        source=PaperSource.SEMANTIC_SCHOLAR,
        query="q",
        venue_filters=venue_filters or [],
        min_citations=min_citations,
    )


def test_no_filters_keeps_all():
    papers = [_paper("a"), _paper("b")]
    assert _apply_spec_filters(papers, _spec()) == papers


def test_citation_floor_filters():
    papers = [_paper("a", citations=5), _paper("b", citations=120), _paper("c", citations=0)]
    kept = _apply_spec_filters(papers, _spec(min_citations=100))
    assert [p.id for p in kept] == ["b"]
    assert _apply_spec_filters(papers, _spec(min_citations=0)) == papers


def test_venue_filter_token_overlap():
    papers = [
        _paper("ok-exact", venue="SIGSPATIAL 2015"),
        _paper("ok-bare", venue="SIGSPATIAL"),
        _paper("noise", venue="NeurIPS 2023"),
        _paper("empty", venue=""),
    ]
    kept = _apply_spec_filters(papers, _spec(venue_filters=["SIGSPATIAL"]))
    assert {p.id for p in kept} == {"ok-exact", "ok-bare"}
    # Short target matches only exact (case-insensitive) — no token fallback.
    kept2 = _apply_spec_filters(papers, _spec(venue_filters=["gis"]))
    assert {p.id for p in kept2} == set()


def test_venue_and_citation_combined():
    papers = [
        _paper("a", venue="SIGSPATIAL", citations=300),
        _paper("b", venue="SIGSPATIAL", citations=10),
        _paper("c", venue="NeurIPS", citations=500),
    ]
    kept = _apply_spec_filters(papers, _spec(venue_filters=["SIGSPATIAL"], min_citations=100))
    assert [p.id for p in kept] == ["a"]


def test_invalid_citation_count_treated_as_zero():
    papers = [_paper("a", citations=99, venue="x")]
    papers[0].metadata["citation_count"] = "N/A"
    assert _apply_spec_filters(papers, _spec(min_citations=100)) == []