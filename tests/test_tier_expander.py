"""P2.6 tier expander — layered QuerySpec expansion, arXiv capability
boundary, and per-tier budget allocation."""

from __future__ import annotations

from conflux.core.p2_contracts import (
    PaperSource,
    ProjectResearchConfig,
    Track,
    TrackQuery,
)
from conflux.paper_radar.tier_expander import (
    ARXIV_CAPABLE_TIERS,
    TIER_ORDER,
    TIER_SORT,
    TIER_WINDOW_YEARS,
    expand_tier_specs,
    resolve_tiers,
    tier_max_results,
)


def _config(**overrides) -> ProjectResearchConfig:
    defaults = dict(
        profile="profiles/test.yaml",
        max_candidates=100,
        sources=[PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR],
    )
    defaults.update(overrides)
    return ProjectResearchConfig(**defaults)


def _track() -> Track:
    return Track(
        id="geo_agents",
        name="Geospatial AI Agents",
        budget_ratio=0.4,
        queries=[
            TrackQuery(terms="GIS agent OR geospatial LLM", categories=["cs.AI"], priority=90),
        ],
    )


def test_resolve_tiers_defaults_to_all_four():
    tq = TrackQuery(terms="q")
    assert resolve_tiers(tq, _config()) == list(TIER_ORDER)


def test_resolve_tiers_config_override():
    tq = TrackQuery(terms="q")
    cfg = _config(coverage_tiers=["frontier", "classic"])
    assert resolve_tiers(tq, cfg) == ["frontier", "classic"]


def test_resolve_tiers_track_query_override_wins():
    tq = TrackQuery(terms="q", tiers=["hot"])
    cfg = _config(coverage_tiers=["frontier", "classic"])
    assert resolve_tiers(tq, cfg) == ["hot"]


def test_expand_four_tiers_two_sources():
    cfg = _config(max_candidates=100)
    specs = expand_tier_specs(_track(), _track().queries[0], cfg)
    # frontier: arXiv + S2; hot: arXiv + S2; milestone: S2 only; classic: S2 only
    assert len(specs) == 6
    tiers = {spec.coverage_tier for spec in specs}
    assert tiers == {"frontier", "hot", "milestone", "classic"}
    for spec in specs:
        if spec.source == PaperSource.ARXIV:
            assert spec.coverage_tier in ARXIV_CAPABLE_TIERS
        assert spec.sort_by == TIER_SORT[spec.coverage_tier]
        years = TIER_WINDOW_YEARS[spec.coverage_tier]
        assert spec.year_from is not None
        assert spec.year_to is not None
        assert spec.year_to - spec.year_from + 1 <= years + 1


def test_expand_hot_only_config():
    cfg = _config(coverage_tiers=["hot"])
    specs = expand_tier_specs(_track(), _track().queries[0], cfg)
    assert len(specs) == 2  # arXiv + S2 for hot
    assert all(spec.coverage_tier == "hot" for spec in specs)


def test_tier_budget_allocation_respects_cap():
    cfg = _config(max_candidates=100)
    track = _track()  # budget_ratio=0.4 -> 40, single query
    for tier in TIER_ORDER:
        per_tier = tier_max_results(
            track, cfg, query_count=1, tier=tier
        )
        assert 10 <= per_tier <= 50
    # 40 * quota: frontier 12 / hot 16 / milestone 8 / classic 4, floored at 10.
    assert tier_max_results(track, cfg, query_count=1, tier="frontier") == 12
    assert tier_max_results(track, cfg, query_count=1, tier="hot") == 16
    assert tier_max_results(track, cfg, query_count=1, tier="milestone") == 10
    assert tier_max_results(track, cfg, query_count=1, tier="classic") == 10
    specs = expand_tier_specs(track, track.queries[0], cfg)
    total = sum(spec.max_results for spec in specs)
    # 6 specs x the per-tier budget.
    assert total == 12 + 12 + 16 + 16 + 10 + 10


def test_tier_sort_mapping():
    assert TIER_SORT["frontier"] == "submittedDate"
    assert TIER_SORT["hot"] == "relevance"
    assert TIER_SORT["milestone"] == "citationCount"
    assert TIER_SORT["classic"] == "citationCount"


def test_classic_spec_carries_venue_filters_and_citation_floor():
    """Classic tier specs carry target_venues (up to 5) + classic_min_citations."""
    from conflux.research_profile import load_profile

    cfg = _config(max_candidates=100, classic_min_citations=50)
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    specs = expand_tier_specs(_track(), _track().queries[0], cfg, profile=profile)
    classic_specs = [s for s in specs if s.coverage_tier == "classic"]
    assert classic_specs, "classic tier should produce S2-only specs"
    for spec in classic_specs:
        assert spec.source == PaperSource.SEMANTIC_SCHOLAR
        assert spec.min_citations == 50
        # venue_filters = profile.target_venues[:5] (or [] when absent)
        assert len(spec.venue_filters) <= 5
        # classic window = classic_years (20 by default)
        now = __import__("datetime").datetime.now().year
        assert spec.year_to == now
        assert spec.year_to - spec.year_from + 1 <= 21
    # non-classic tiers never carry a citation floor
    for spec in specs:
        if spec.coverage_tier != "classic":
            assert spec.min_citations is None
    # modifying the profile target venues propagates (empty -> venue_filters [])
    from conflux.research_profile.models import ResearchProfile

    bare = ResearchProfile(
        id="x", name="x", fields=[], research_questions=[], keywords=[],
        target_venues=[],
    )
    specs2 = expand_tier_specs(_track(), _track().queries[0], cfg, profile=bare)
    assert all(s.venue_filters == [] for s in specs2 if s.coverage_tier == "classic")
