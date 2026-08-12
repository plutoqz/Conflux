"""Resolve Track definitions into executable QuerySpec objects.

Takes a ResearchProfile (with tracks) and ProjectResearchConfig, expands
each Track's queries into fully-resolved QuerySpec objects ready for
execution against paper sources.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from conflux.core.p2_contracts import (
    PaperSource,
    ProjectResearchConfig,
    ProjectResearchContext,
    QuerySpec,
    Track,
    TrackQuery,
)
from conflux.research_profile.models import ResearchProfile

from .tier_expander import expand_tier_specs


def resolve_query_specs_from_profile(
    profile: ResearchProfile,
    config: ProjectResearchConfig | None = None,
    context: ProjectResearchContext | None = None,
) -> list[QuerySpec]:
    """Resolve all Track queries from a profile into QuerySpec objects."""
    tracks = profile.get_tracks()
    if not tracks:
        return _fallback_query_specs(profile, config, context)
    return resolve_query_specs(tracks, config=config, context=context, profile=profile)


def resolve_query_specs(
    tracks: list[Track],
    config: ProjectResearchConfig | None = None,
    context: ProjectResearchContext | None = None,
    profile: Any = None,
) -> list[QuerySpec]:
    """Expand a list of Tracks into executable QuerySpec objects.

    Each TrackQuery in a Track becomes one QuerySpec per coverage tier and
    per enabled source (P2.6 layered coverage).  When ``config`` is None a
    default ProjectResearchConfig (arXiv + Semantic Scholar, four tiers) is
    used.  ``profile`` (optional) supplies target venues for the classic
    tier's venue filters.
    """
    effective_config = config or ProjectResearchConfig(
        profile="",
        sources=[PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR],
    )
    profile_version = context.profile_version if context else ""
    context_version = context.project_revision if context else ""

    specs: list[QuerySpec] = []
    for track in tracks:
        for tq in track.queries:
            specs.extend(expand_tier_specs(
                track,
                tq,
                effective_config,
                profile_version=profile_version,
                context_version=context_version,
                profile=profile,
            ))
    return specs


def _fallback_query_specs(
    profile: ResearchProfile,
    config: ProjectResearchConfig | None = None,
    context: ProjectResearchContext | None = None,
) -> list[QuerySpec]:
    """Generate fallback QuerySpecs when no Tracks are defined.

    Uses profile keywords and research questions to build simple queries.
    This mirrors the legacy profile_arxiv_queries behavior.
    """
    sources: list[PaperSource] = (
        config.sources if config
        else [PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR]
    )
    max_results = config.max_candidates if config else 100
    profile_version = context.profile_version if context else ""
    context_version = context.project_revision if context else ""

    specs: list[QuerySpec] = []

    # Keyword-based queries
    for kw in profile.keywords[:5]:
        for source in sources:
            specs.append(QuerySpec(
                id=_spec_id(source.value, kw),
                track_id="",
                source=source,
                query=kw,
                categories=[],
                date_window_days=365,
                max_results=min(max_results // max(1, len(profile.keywords)), 30),
                priority=50,
                provenance="fallback_keyword",
                profile_version=profile_version,
                context_version=context_version,
            ))

    # Venue-targeted queries
    for venue in profile.target_venues[:3]:
        for source in sources:
            specs.append(QuerySpec(
                id=_spec_id(source.value, f"venue:{venue}"),
                track_id="",
                source=source,
                query=venue,
                categories=[],
                date_window_days=365,
                max_results=min(max_results // max(1, len(profile.target_venues)), 20),
                priority=40,
                provenance="fallback_venue",
                profile_version=profile_version,
                context_version=context_version,
            ))

    # Scholar queries
    for scholar in profile.tracked_scholars[:5]:
        for source in sources:
            specs.append(QuerySpec(
                id=_spec_id(source.value, f"scholar:{scholar}"),
                track_id="",
                source=source,
                query=scholar,
                categories=[],
                date_window_days=730,
                max_results=10,
                priority=55,
                provenance="fallback_scholar",
                profile_version=profile_version,
                context_version=context_version,
            ))

    return specs


def _spec_id(source: str, query: str) -> str:
    """Deterministic short id for a source+query pair."""
    raw = json.dumps({"s": source, "q": query}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
