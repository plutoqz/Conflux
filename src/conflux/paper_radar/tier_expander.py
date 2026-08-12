"""P2.6 layered coverage — expand a TrackQuery into per-tier QuerySpecs.

Each TrackQuery expands into one QuerySpec per coverage tier
(frontier / hot / milestone / classic).  arXiv serves frontier
(submittedDate) and hot (relevance) only; milestone/classic are served by
Semantic Scholar with citation sorting, because arXiv exposes no citation
counts.

Tier budgets are derived from the track's share of ``config.max_candidates``
split by the per-tier quota (DEFAULT_TIER_QUOTA).  This keeps the total
candidate pool bounded while widening it from a single window to four.
"""

from __future__ import annotations

from datetime import datetime

from conflux.core.p2_contracts import (
    DEFAULT_TIER_QUOTA,
    PaperSource,
    ProjectResearchConfig,
    QuerySpec,
    Track,
    TrackQuery,
)

# Tier -> look-back window in years.
TIER_WINDOW_YEARS: dict[str, int] = {
    "frontier": 1,
    "hot": 3,
    "milestone": 10,
    "classic": 20,
}

# Floor for classic-tenure venue matching — venues may be named "SIGSPATIAL
# 2015" / "NeurIPS" or bare "ACM SIGSPATIAL"; a simple token-level fallback
# keeps curated venue lists useful without false positives.
VENUE_SUBSTRING_MIN_LEN = 6

# Tier -> sort key passed to the source API / client-side re-sort.
TIER_SORT: dict[str, str] = {
    "frontier": "submittedDate",
    "hot": "relevance",
    "milestone": "citationCount",
    "classic": "citationCount",
}

# Tiers arXiv can serve (arXiv has no citation counts).
ARXIV_CAPABLE_TIERS: frozenset[str] = frozenset({"frontier", "hot"})

TIER_ORDER: tuple[str, ...] = ("frontier", "hot", "milestone", "classic")


def resolve_tiers(
    track_query: TrackQuery,
    config: ProjectResearchConfig | None,
) -> list[str]:
    """Return the ordered tier list for a TrackQuery.

    Priority: TrackQuery.tiers > config.coverage_tiers > all four tiers.
    """
    if track_query.tiers:
        return [tier for tier in TIER_ORDER if tier in track_query.tiers]
    if config is not None and config.coverage_tiers:
        return [tier for tier in TIER_ORDER if tier in config.coverage_tiers]
    return list(TIER_ORDER)


def tier_max_results(
    track: Track,
    config: ProjectResearchConfig,
    *,
    query_count: int,
    tier: str,
) -> int:
    """Per-spec fetch size for a tier, from the track's share of the budget.

    The track budget (``max_candidates * budget_ratio``) is split by the
    tier quota (DEFAULT_TIER_QUOTA), then divided across the queries in the
    track.  Each enabled source fetches up to this many raw results; sources
    are disjoint so the tier's pool is their union after de-dup.  A floor of
    10 keeps built-in small pools usable and a per-spec cap of 50 matches the
    pre-P2.6 legacy cap.
    """
    track_budget = max(1, int(config.max_candidates * (track.budget_ratio or 1.0)))
    query_count = max(1, query_count)
    quota = DEFAULT_TIER_QUOTA.get(tier, 0.25)
    per_spec = max(10, int(track_budget * quota) // query_count)
    return min(per_spec, 50)


def _match_venue(venue: str, target: str) -> bool:
    """Exact / case-insensitive / token-match a paper venue against a target.

    '' targets and targets shorter than ``VENUE_SUBSTRING_MIN_LEN`` match
    exactly (case-insensitive) only — prevents over-broad matches from short
    acronyms.
    """
    if not venue or not target:
        return False
    venue = str(venue).strip()
    target = str(target).strip()
    if venue == target:
        return True
    if venue.casefold() == target.casefold():
        return True
    if len(target) >= VENUE_SUBSTRING_MIN_LEN and target.casefold() in venue.casefold():
        return True
    return False


def _resolve_venue_filters(
    tier: str,
    profile: Any,
    config: ProjectResearchConfig,
) -> list[str]:
    """Venue constraints for the classic tier (plan §3.1, §3.4).

    Up to 5 profile target venues constrain the classic layer; absent
    targets, the tier relies on the citation floor (``min_citations`` on the
    spec) alone.
    """
    if tier != "classic":
        return []
    venues = [str(v).strip() for v in (profile.target_venues or []) if str(v).strip()][:5]
    return venues


def expand_tier_specs(
    track: Track,
    track_query: TrackQuery,
    config: ProjectResearchConfig,
    *,
    profile_version: str = "",
    context_version: str = "",
    profile: Any = None,
) -> list[QuerySpec]:
    """Expand one TrackQuery into per-tier QuerySpecs across enabled sources.
    """
    sources: list[PaperSource] = (
        config.sources
        if config.sources
        else [PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR]
    )
    tiers = resolve_tiers(track_query, config)
    now_year = datetime.now().year
    query_count = max(1, len(track.queries))
    if profile is None:
        from conflux.research_profile.models import ResearchProfile

        profile = ResearchProfile(id="", name="", fields=[], research_questions=[], keywords=[])

    specs: list[QuerySpec] = []
    for tier in tiers:
        years = (config.classic_years if tier == "classic" else
                 config.milestone_years if tier == "milestone" else
                 TIER_WINDOW_YEARS[tier])
        year_from = now_year - years + 1
        year_to = now_year
        sort_by = TIER_SORT[tier]
        final_query = track_query.terms
        if track_query.suffix:
            final_query = f"({track_query.terms}) AND ({track_query.suffix})"
        venue_filters = _resolve_venue_filters(tier, profile, config)
        for source in sources:
            if source == PaperSource.ARXIV and tier not in ARXIV_CAPABLE_TIERS:
                continue
            spec = QuerySpec(
                id=_tier_spec_id(source.value, track.id, tier, final_query),
                track_id=track.id,
                source=source,
                query=final_query,
                categories=list(track_query.categories or []),
                date_window_days=max(1, years * 365),
                max_results=tier_max_results(
                    track,
                    config,
                    query_count=query_count,
                    tier=tier,
                ),
                priority=track_query.priority,
                provenance="track_manual",
                profile_version=profile_version,
                context_version=context_version,
                coverage_tier=tier,  # type: ignore[arg-type]
                year_from=year_from,
                year_to=year_to,
                sort_by=sort_by,  # type: ignore[arg-type]
                offset=0,
                venue_filters=venue_filters,
                min_citations=(
                    config.classic_min_citations
                    if tier == "classic"
                    else None
                ),
                skip_ingested=True,
            )
            specs.append(spec)
    return specs


def _tier_spec_id(source: str, track_id: str, tier: str, terms: str) -> str:
    import hashlib
    import json

    raw = json.dumps(
        {"s": source, "t": track_id, "ti": tier, "q": terms},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
