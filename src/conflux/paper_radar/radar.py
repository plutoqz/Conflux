"""P2 Paper Radar — main pipeline orchestrator.

Assembles project context, generates intents, resolves queries, runs the paper
ingestion pipeline against real sources, and produces a RadarRunResult with
project-scoped paper links and impact suggestions.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from conflux.core.p2_contracts import (
    DEFAULT_TIER_REFRESH_DAYS,
    EvidenceUtility,
    PaperIdentity,
    PaperLinkStatus,
    PaperSource,
    ProjectPaperLink,
    ProjectResearchConfig,
    QuerySpec,
    RadarRunResult,
    RadarRunStats,
)
from conflux.model_factory import create_embedding_model
from conflux.paper_ingestion.dedup import deduplicate_papers
from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_ingestion.scorer import score_paper
from conflux.project_registry.models import ProjectDefinition
from conflux.research_profile import ResearchProfile, load_profile

from .context_builder import build_project_research_context
from .deep_analyzer import run_deep_analysis
from .intent_generator import generate_search_intents
from .query_builder import resolve_query_specs_from_profile


def run_paper_radar_from_profile(
    project: ProjectDefinition,
    profile_path: str | Path,
    *,
    audit: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
    llm_review: bool = False,
    review_model: Any = None,
    layered_review: bool = False,
    review_mode: str = "pointwise",
    review_few_shot: bool = False,
    review_chunk_size: int = 8,
    seen_state: dict[str, Any] | None = None,
    persist_seen_file: bool = True,
    db: Any = None,
    force_refresh: bool = False,
) -> RadarRunResult:
    """Convenience wrapper that loads a profile and runs the radar."""
    profile = load_profile(profile_path, validate=False)
    return run_paper_radar(
        project=project,
        profile=profile,
        audit=audit,
        out_dir=out_dir,
        llm_review=llm_review,
        review_model=review_model,
        layered_review=layered_review,
        review_mode=review_mode,
        review_few_shot=review_few_shot,
        review_chunk_size=review_chunk_size,
        seen_state=seen_state,
        persist_seen_file=persist_seen_file,
        db=db,
        force_refresh=force_refresh,
    )


def run_paper_radar(
    project: ProjectDefinition,
    profile: ResearchProfile,
    *,
    audit: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
    llm_review: bool = False,
    review_model: Any = None,
    embedding_model: Any = None,
    layered_review: bool = False,
    review_mode: str = "pointwise",
    review_few_shot: bool = False,
    review_chunk_size: int = 8,
    seen_state: dict[str, Any] | None = None,
    persist_seen_file: bool = True,
    db: Any = None,
    force_refresh: bool = False,
    query_specs: list | None = None,
) -> RadarRunResult:
    """Run the full P2 paper radar pipeline for a project.

    Steps:
    1. Build ProjectResearchContext from project + profile + audit
    2. Generate SearchIntent list
    3. Resolve QuerySpec list from profile tracks (or fallback); when
       ``query_specs`` is provided it is used instead (programmatic
       callers / tests can customise specs, e.g. skip_ingested=False)
    4. Execute queries against paper sources (P2.6 layered coverage, with
       retrieval cursors when ``db`` is provided; low-frequency tiers skip
       re-retrieval unless ``force_refresh``)
    5. De-duplicate, filter (incl. global ingested-paper exclusion),
       create ProjectPaperLink entries
    6. Produce RadarRunResult

    ``db`` (optional SQLiteDatabase) enables: retrieval cursors for
    milestone/classic tiers and exclusion of already-ingested papers.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = time.time()

    # Resolve project research config
    config_raw = project.research or {}
    config = _parse_config(config_raw, profile)

    # Step 1: Build context
    context = build_project_research_context(project, profile, audit=audit)

    # Step 2: Generate intents
    intents = generate_search_intents(context, llm_review=llm_review, llm_model=review_model)

    # Step 3: Resolve query specs (profile feeds classic-tier venue filters);
    # programmatic callers may inject pre-built specs instead.
    queries = query_specs if query_specs is not None else resolve_query_specs_from_profile(
        profile, config=config, context=context,
    )

    # P2.6: drop specs whose tier is not due for refresh (retrieval cursors).
    cursor_store = None
    if db is not None:
        from conflux.adapters.sqlite_store import RetrievalCursorStore

        cursor_store = RetrievalCursorStore(db)
        kept: list = []
        for spec in queries:
            tier = str(getattr(spec, "coverage_tier", "") or "hot")
            refresh_days = int((config.tier_refresh_days or {}).get(tier, 0))
            if cursor_store.should_refresh(
                profile.id,
                str(spec.track_id or ""),
                tier,
                refresh_days,
                force=force_refresh,
            ):
                kept.append(spec)
        skipped_tiers = len(queries) - len(kept)
        queries = kept
    else:
        skipped_tiers = 0

    # Stats are created up-front so query execution and deep analysis can
    # record telemetry (query-level results, LLM calls, tokens).
    stats = RadarRunStats(
        project_id=project.id,
        run_id=run_id,
        started_at=__import__("datetime").datetime.utcnow(),
    )
    stats.query_count = len(queries)
    stats.skipped_cursor_tiers = skipped_tiers

    # Step 4: Execute queries against sources.
    all_papers, failed_sources, exempt_ids = _execute_queries(queries, stats=stats, db=db)

    # P2.6 citation seeds: expand from known papers when enabled.
    citation_seed_added = 0
    no_citation_seeds = False
    if config.citation_seed_enabled and db is not None:
        from conflux.paper_radar.seed_expander import collect_citation_seeds

        seed_papers = collect_citation_seeds(
            db,
            profile=profile,
            config=config,
            seen_keys=_seen_keys(seen_state or {}),
        )
        if seed_papers is None:
            no_citation_seeds = True
        else:
            all_papers.extend(seed_papers)
            citation_seed_added = len(seed_papers)
    stats.citation_seed_added = citation_seed_added
    stats.no_citation_seeds = no_citation_seeds

    # Step 5: De-duplicate (incl. cross-source arxiv_id ↔ S2 merges) and
    # filter.
    unique_papers = _deduplicate_papers(all_papers)

    # P2.6: exclude globally-ingested papers (cross-profile).  Runs on the
    # canonical pool (after cross-source normalization, so an S2 record with
    # an arXiv external id matches 'arxiv:<id>'), honoring per-spec
    # skip_ingested: a paper brought in by at least one skip_ingested=False
    # spec is kept.  Telemetry counts unique excluded papers.
    if db is not None:
        from conflux.adapters.sqlite_store import list_ingested_paper_keys

        ingested_keys = list_ingested_paper_keys(db)
        exempt = exempt_ids
        if ingested_keys:
            before = len(unique_papers)
            unique_papers = [
                paper for paper in unique_papers
                if paper.id in exempt
                or _paper_record_key(paper) not in ingested_keys
            ]
            stats.excluded_ingested = before - len(unique_papers)

    filtered_papers = _apply_negative_filters(unique_papers, profile)
    # Embedding coarse rank (planned P2 stage). No silent lexical fallback:
    # an unavailable embedding model fails the run so it can be reported.
    from .coarse_rank import embedding_coarse_rank

    model = embedding_model if embedding_model is not None else create_embedding_model()
    ranked = embedding_coarse_rank(
        filtered_papers,
        profile,
        context,
        embedding_model=model,
    )
    ranked = ranked[:config.max_candidates]
    score_by_id = {paper.id: combined for paper, combined, _ in ranked}

    # Batch LLM semantic review (planned P2.8): a bounded pool is reviewed and
    # the LLM relevance re-ranks the links.  Review failures are unreviewed
    # (needs_review) and never auto-promoted.
    if llm_review and review_model is not None and config.semantic_review_limit > 0:
        from .semantic_review import (
            REVIEW_THRESHOLD_HIGH,
            REVIEW_THRESHOLD_LOW,
            batch_semantic_review,
        )

        if layered_review:
            # Layered review: high-score candidates are accepted directly (no
            # LLM call, so the LLM cannot down-weight them); low-score
            # candidates are rejected directly; only the fuzzy band is
            # reviewed by the LLM.
            review_pool = [
                (paper, combined)
                for paper, combined, _ in ranked
                if REVIEW_THRESHOLD_LOW <= combined < REVIEW_THRESHOLD_HIGH
            ]
        else:
            review_pool = [
                (paper, combined) for paper, combined, _ in ranked
            ]
        review_pool = review_pool[: config.semantic_review_limit]
        reviews = batch_semantic_review(
            [
                {"id": paper.id, "title": paper.title, "abstract": paper.abstract or ""}
                for paper, _ in review_pool
            ],
            context,
            review_model,
            max_papers=config.semantic_review_limit,
            profile_keywords=[str(item) for item in (profile.keywords or [])],
            stats=stats,
            mode=review_mode,
            few_shot=review_few_shot,
            chunk_size=review_chunk_size,
        )
        stats.semantic_review_count = len(reviews)
        for paper, _ in review_pool:
            review = reviews.get(paper.id)
            if review is not None and review.reviewed:
                score_by_id[paper.id] = review.relevance
            elif review is not None and paper.id not in stats.needs_review_paper_ids:
                stats.needs_review_paper_ids.append(paper.id)

    ranked_papers = [paper for paper, _, _ in ranked]
    paper_map: dict[str, PaperRecord] = {p.id: p for p in ranked_papers}

    # Step 6: Create project-paper links
    links = _create_project_links(
        papers=ranked_papers,
        project_id=project.id,
        intents=intents,
        context=context,
        relevance_scores=score_by_id,
    )

    # Step 7: Run deep analysis on top-N papers (D: full-text evidence)
    suggestions: list[ProjectImpactSuggestion] = []
    deep_read = 0
    # Project-scoped seen state: stable rejects are not re-reviewed.
    project_seen = seen_state if seen_state is not None else (
        _load_project_seen(out_dir, project.id) if out_dir else {}
    )
    skipped_seen_rejected = 0
    shortlisted_links = [link for link in links if link.status == PaperLinkStatus.SHORTLISTED]
    if config.deep_read_limit > 0 and shortlisted_links:
        deep_pairs = []
        for link in shortlisted_links:
            seen_key = _seen_key(link)
            if seen_key in project_seen and project_seen[seen_key].get("status") == "rejected":
                skipped_seen_rejected += 1
                continue
            deep_pairs.append(
                (link, paper_map.get(link.paper_identity.canonical_id, {}).to_dict()
                 if paper_map.get(link.paper_identity.canonical_id)
                 else {"id": link.paper_identity.canonical_id})
            )
        # Semantic LLM deep analysis (Phase P2): review_model is a chat model
        # created by the caller; llm_review gates the LLM path.  Without it,
        # deterministic keyword analysis is used as the safety net.
        if deep_pairs:
            llm_model = review_model if (llm_review and review_model is not None) else None
            suggestions = run_deep_analysis(
                deep_pairs,
                context,
                intents,
                download_dir=(Path(out_dir) / "pdf_cache") if out_dir else None,
                max_papers=config.deep_read_limit,
                llm_model=llm_model,
                stats=stats,
            )
        deep_read = min(len(deep_pairs), config.deep_read_limit)
        stats.skipped_seen_rejected = skipped_seen_rejected

    # Unreviewed links (semantic review or deep-analysis failures) are marked
    # needs_review regardless of deep-read configuration.
    if stats.needs_review_paper_ids:
        needs_review_ids = set(stats.needs_review_paper_ids)
        for link in links:
            if link.paper_identity.canonical_id in needs_review_ids:
                link.status = PaperLinkStatus.NEEDS_REVIEW
        stats.needs_review = len(needs_review_ids)

    # Write output if out_dir specified
    if out_dir and persist_seen_file:
        _save_project_seen(out_dir, project.id, links)
    if out_dir:
        _write_radar_output(out_dir, project.id, run_id, context, intents, queries, links)

    elapsed = time.time() - started_at
    stats.total_candidates = len(all_papers)
    stats.after_dedup = len(unique_papers)
    stats.after_negative_filter = len(filtered_papers)
    stats.after_coarse_rank = len(ranked_papers)
    stats.shortlisted = sum(1 for l in links if l.status == PaperLinkStatus.SHORTLISTED)
    stats.deep_read = deep_read
    stats.saved = sum(1 for l in links if l.status == PaperLinkStatus.SAVED)
    stats.rejected = sum(1 for l in links if l.status == PaperLinkStatus.REJECTED)
    stats.suggestions_proposed = len(suggestions)
    stats.sources_used = [s.value for s in config.sources]
    stats.failed_sources = failed_sources
    stats.intent_count = len(intents)
    stats.query_count = len(queries)
    stats.finished_at = __import__("datetime").datetime.utcnow()
    stats.elapsed_seconds = elapsed

    # P2.6: persist retrieval cursors for the tiers actually executed.
    if cursor_store is not None:
        _record_cursors(cursor_store, profile.id, queries, run_id, stats.query_stats)

    return RadarRunResult(
        project_id=project.id,
        context=context,
        intents=intents,
        queries=queries,
        links=links,
        suggestions=suggestions,
        stats=stats,
    )


def _parse_config(raw: dict[str, Any], profile: ResearchProfile) -> ProjectResearchConfig:
    """Parse project YAML 'research' section into a ProjectResearchConfig, with defaults."""
    raw_tiers = raw.get("coverage_tiers")
    tiers = None
    if isinstance(raw_tiers, list):
        valid = {"frontier", "hot", "milestone", "classic"}
        tiers = [t for t in raw_tiers if t in valid] or None
    raw_refresh = raw.get("tier_refresh_days") or {}
    refresh_days = {
        tier: int(raw_refresh.get(tier, DEFAULT_TIER_REFRESH_DAYS.get(tier, 0)))
        for tier in ("frontier", "hot", "milestone", "classic")
    }
    return ProjectResearchConfig(
        profile=raw.get("profile", f"profiles/{profile.id}.yaml"),
        sources=_parse_sources(raw.get("sources", ["arxiv", "semantic_scholar"])),
        cadence=raw.get("cadence", "manual"),
        max_candidates=int(raw.get("max_candidates", 100)),
        deep_read_limit=int(raw.get("deep_read_limit", 5)),
        semantic_review_limit=int(raw.get("semantic_review_limit", 40)),
        auto_generate_queries=bool(raw.get("auto_generate_queries", True)),
        require_query_review=bool(raw.get("require_query_review", True)),
        require_plan_writeback_approval=bool(raw.get("require_plan_writeback_approval", True)),
        track_overrides=list(raw.get("track_overrides") or []),
        coverage_tiers=tiers,
        classic_min_citations=int(raw.get("classic_min_citations", 100)),
        classic_years=int(raw.get("classic_years", 20)),
        milestone_years=int(raw.get("milestone_years", 10)),
        tier_refresh_days=refresh_days,
        citation_seed_enabled=bool(raw.get("citation_seed_enabled", True)),
        citation_seed_hop=int(raw.get("citation_seed_hop", 2)),
        citation_seed_per_paper=int(raw.get("citation_seed_per_paper", 20)),
        citation_seed_budget=int(raw.get("citation_seed_budget", 100)),
    )


def _parse_sources(raw: list[str] | str | None) -> list[PaperSource]:
    """Parse source strings into PaperSource enum values."""
    if not raw:
        return [PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR]
    if isinstance(raw, str):
        raw = [raw]
    result: list[PaperSource] = []
    for s in raw:
        s = str(s).strip().lower()
        try:
            result.append(PaperSource(s))
        except ValueError:
            continue
    return result or [PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR]


def _execute_queries(
    queries: list,
    stats: RadarRunStats | None = None,
    db: Any = None,
) -> tuple[list[PaperRecord], list[str]]:
    """Execute QuerySpec objects against their paper sources.

    Returns (all_papers, failed_sources).
    Falls back gracefully when a source is unavailable.  When ``stats`` is
    provided, per-query results are recorded for query-level reporting.
    P2.6: each QuerySpec carries tier/year/sort/offset so the sources can
    serve layered coverage (frontier/hot via arXiv, milestone/classic via S2).
    After retrieval, spec-level filters are applied: classic venue +
    citation floor, and ingested-paper exclusion when ``db`` is provided and
    the spec's ``skip_ingested`` is set (default on).  The counted/kept
    papers are what enter the tier pool.
    """
    import logging

    from conflux.paper_ingestion.arxiv_source import search_arxiv
    from conflux.paper_ingestion.semantic_scholar_source import search_semantic_scholar

    logger = logging.getLogger(__name__)
    all_papers: list[PaperRecord] = []
    failed: set[str] = set()
    per_query: list[dict[str, Any]] = []
    exempt_ids: set[str] = set()  # papers from skip_ingested=False specs

    if db is not None:
        from conflux.adapters.sqlite_store import list_ingested_paper_keys

        ingested_keys = list_ingested_paper_keys(db)

    for spec in queries:
        query_id = str(spec.id or "")
        entry: dict[str, Any] = {
            "query_id": query_id,
            "track_id": str(spec.track_id or ""),
            "source": str(spec.source.value if hasattr(spec.source, "value") else spec.source),
            "coverage_tier": str(getattr(spec, "coverage_tier", "") or ""),
            "candidate_count": 0,
            "failed": False,
        }
        try:
            if spec.source == PaperSource.ARXIV:
                sort_by = (
                    "submittedDate"
                    if getattr(spec, "coverage_tier", "") == "frontier"
                    else "relevance"
                )
                papers = search_arxiv(
                    spec.query,
                    max_results=spec.max_results,
                    start=int(getattr(spec, "offset", 0) or 0),
                    categories=list(getattr(spec, "categories", None) or []),
                    sort_by=sort_by,
                )
            elif spec.source == PaperSource.SEMANTIC_SCHOLAR:
                papers = search_semantic_scholar(
                    spec.query,
                    max_results=spec.max_results,
                    offset=int(getattr(spec, "offset", 0) or 0),
                    year_from=getattr(spec, "year_from", None),
                    year_to=getattr(spec, "year_to", None),
                    sort=str(getattr(spec, "sort_by", "relevance") or "relevance"),
                )
                papers = _apply_spec_filters(papers, spec)
            else:
                logger.warning("Unknown source: %s", spec.source)
                failed.add(str(spec.source.value))
                entry["failed"] = True
                per_query.append(entry)
                continue
            if db is not None and not getattr(spec, "skip_ingested", True):
                # Papers from a skip_ingested=False spec are exempt from the
                # pool-level ingested exclusion.
                exempt_ids.update(p.id for p in papers)
            entry["skip_ingested"] = bool(getattr(spec, "skip_ingested", True))
            entry["candidate_count"] = len(papers)
            all_papers.extend(papers)
        except Exception:
            failed.add(spec.source.value)
            entry["failed"] = True
        per_query.append(entry)

    if stats is not None:
        stats.query_stats = per_query
    return all_papers, sorted(failed), exempt_ids


def _paper_record_key(paper: PaperRecord) -> str:
    """Global paper_key for a PaperRecord, matching sqlite_store._paper_key."""
    doi = str(paper.doi or "").strip().casefold()
    if doi:
        return f"doi:{doi}"
    source = str(paper.source or "unknown").strip().casefold()
    canonical_id = str(paper.id or "").strip()
    if not canonical_id:
        raise ValueError("paper record requires id")
    return f"{source}:{canonical_id}"


def _ingest_excluded(
    paper_key: str,
    ingested_keys: set[str],
    excluded: set[str],
) -> bool:
    """True when ``paper_key`` is ingested and not yet recorded as excluded.

    Records the key into ``excluded`` so telemetry counts unique papers.
    """
    if paper_key not in ingested_keys:
        return False
    excluded.add(paper_key)
    return True


def _deduplicate_papers(papers: list[PaperRecord]) -> list[PaperRecord]:
    """Total-pool de-duplication, incl. cross-source arxiv_id ↔ S2 merges.

    Cross-source sharing is folded into the record's canonical arxiv key
    first so both sources land on one key: S2 records carrying an arXiv
    external id (``metadata["arxiv_id"]``) are rewritten as the arxiv record
    (version-stripped on both sides), so ``deduplicate_papers`` merges arXiv +
    S2 copies of the same paper and ingested exclusion matches
    'arxiv:<id>'.  Introduced in P2.6.2 to keep the layered frontier/hot
    double-source pool from counting one paper twice.
    """
    canonicalized: list[PaperRecord] = []
    seen_arxiv: set[str] = set()
    for paper in papers:
        meta = paper.metadata or {}
        arxiv_id = str(meta.get("arxiv_id") or "").strip()
        existing_key = _paper_record_key(paper)
        if existing_key.startswith("arxiv:"):
            # arXiv record: strip the version for canonical arxiv id.
            bare = _strip_arxiv_version(str(paper.id or ""))
            if bare not in seen_arxiv:
                seen_arxiv.add(bare)
                canonicalized.append(_as_arxiv(paper, bare))
            continue
        if arxiv_id:
            bare = _strip_arxiv_version(arxiv_id)
            if bare not in seen_arxiv:
                seen_arxiv.add(bare)
                canonicalized.append(_as_arxiv(paper, bare))
            continue
        canonicalized.append(paper)
    return deduplicate_papers(canonicalized)


def _strip_arxiv_version(arxiv_id: str) -> str:
    """'2401.00010v1' -> '2401.00010' (also handles URLs/'.pdf')."""
    text = str(arxiv_id or "").strip()
    if "/abs/" in text:
        text = text.rsplit("/abs/", 1)[1]
    if "/pdf/" in text:
        text = text.rsplit("/pdf/", 1)[1]
    if text.endswith(".pdf"):
        text = text[:-4]
    if "v" in text:
        head, tail = text.rsplit("v", 1)
        if tail.isdigit():
            return head
    return text


def _as_arxiv(paper: PaperRecord, arxiv_id: str) -> PaperRecord:
    """Rewrite a paper record to the arXiv identity (source='arxiv')."""
    return PaperRecord(
        id=arxiv_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        published_at=paper.published_at,
        source="arxiv",
        url=paper.url,
        pdf_url=paper.pdf_url,
        doi=paper.doi,
        venue=paper.venue,
        categories=paper.categories,
        matched_queries=paper.matched_queries,
        metadata=dict(paper.metadata or {}),
    )


def _apply_spec_filters(papers: list[PaperRecord], spec: QuerySpec) -> list[PaperRecord]:
    """Apply per-spec post-retrieval filters (venue, citation floor).

    Venue matching handles year-qualified venue names (e.g. "SIGSPATIAL
    2015") via token overlap with the target name; the citation floor is
    read from ``metadata["citation_count"]``.  Filtered (non-classic, or
    classic that fails the floor) papers are excluded from the tier pool.
    """
    if not spec.venue_filters and not spec.min_citations:
        return papers
    if not spec.venue_filters:
        return [
            p for p in papers
            if _citation_count(p) >= int(spec.min_citations)
        ]
    if not spec.min_citations:
        return [
            p for p in papers
            if _venue_matches_any(p, spec.venue_filters)
        ]
    return [
        p for p in papers
        if _venue_matches_any(p, spec.venue_filters)
        and _citation_count(p) >= int(spec.min_citations)
    ]


def _citation_count(paper: PaperRecord) -> int:
    meta = paper.metadata or {}
    try:
        return int(meta.get("citation_count") or 0)
    except (TypeError, ValueError):
        return 0


def _venue_matches_any(paper: PaperRecord, targets: list[str]) -> bool:
    """Token-overlap match of a paper venue against target venue names.

    ``venue_filters`` come from ``profile.target_venues`` (potentially
    year-qualified like "SIGSPATIAL 2015"), while S2 ``publicationVenue`` may
    be the bare conference name — match on shared meaningful tokens (len>=4,
    not all-digits) to avoid dropping valid classic-layer results.
    """
    venue = str(paper.venue or "").strip()
    if not venue:
        return False
    venue_tokens = {
        t for t in _tokens(venue)
        if len(t) >= 4 and not t.isdigit()
    }
    if not venue_tokens:
        return False
    for target in targets:
        target_tokens = {
            t for t in _tokens(str(target))
            if len(t) >= 4 and not t.isdigit()
        }
        if target_tokens and target_tokens <= venue_tokens:
            return True
    return False


def _tokens(text: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def _seen_keys(seen_state: dict[str, Any] | None) -> set[str]:
    """Project seen-state keys (stable rejects) used to skip seed expansion."""
    return {str(key) for key in (seen_state or {}).keys() if str(key).strip()}


def _record_cursors(
    cursor_store: Any,
    profile_id: str,
    queries: list,
    run_id: str,
    per_query: list[dict[str, Any]] | None,
) -> None:
    """Persist retrieval cursors for executed specs after a successful run.

    Failed queries (candidate_count == 0 with failed=True) do NOT advance the
    cursor, so a transient source outage does not mark a tier as 'retrieved'.
    """
    if cursor_store is None:
        return
    per_query = per_query or []
    by_query_id = {str(item.get("query_id") or ""): item for item in per_query}
    for spec in queries:
        tier = str(getattr(spec, "coverage_tier", "") or "hot")
        entry = by_query_id.get(str(spec.id or "")) or {}
        if entry.get("failed"):
            continue
        cursor_store.upsert(
            profile_id,
            str(spec.track_id or ""),
            tier,
            run_id=run_id,
            year_from=getattr(spec, "year_from", None),
            year_to=getattr(spec, "year_to", None),
            candidate_count=int(entry.get("candidate_count") or 0),
        )


def _apply_negative_filters(papers: list[PaperRecord], profile: ResearchProfile) -> list[PaperRecord]:
    """Apply negative keyword filtering."""
    from conflux.paper_ingestion.filters import apply_negative_filters
    return apply_negative_filters(papers, profile)


def _create_project_links(
    papers: list[PaperRecord],
    project_id: str,
    intents: list,
    context,
    relevance_scores: dict[str, float] | None = None,
) -> list[ProjectPaperLink]:
    """Create ProjectPaperLink entries for filtered papers."""
    links: list[ProjectPaperLink] = []
    relevance_scores = relevance_scores or {}
    for paper in papers:
        relevance = float(relevance_scores.get(paper.id, 0.0))
        identity = PaperIdentity(
            source=paper.source or "unknown",
            canonical_id=paper.id,
            doi=paper.doi,
        )
        link = ProjectPaperLink(
            project_id=project_id,
            paper_identity=identity,
            status=(
                PaperLinkStatus.SHORTLISTED
                if relevance >= 0.62
                else PaperLinkStatus.DISCOVERED
            ),
            matched_intent_ids=[i.id for i in intents[:3]],  # simplified
            evidence_utility=EvidenceUtility.NONE,
            relevance=relevance,
            profile_version=context.profile_version,
            context_version=context.project_revision,
        )
        links.append(link)
    return links


def _seen_key(link: ProjectPaperLink) -> str:
    """Project-independent paper identity key used in project seen state."""
    identity = link.paper_identity
    return f"{identity.source}:{identity.canonical_id}"


def _project_seen_path(out_dir: str | Path, project_id: str) -> Path:
    return Path(out_dir) / project_id / "papers" / "seen.json"


def _load_project_seen(out_dir: str | Path, project_id: str) -> dict[str, Any]:
    """Load project-scoped seen state; missing/corrupt state is treated as empty."""
    import json as _json
    path = _project_seen_path(out_dir, project_id)
    if not path.exists():
        return {}
    try:
        payload = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_project_seen(out_dir: str | Path, project_id: str, links: list[ProjectPaperLink]) -> None:
    """Persist project-scoped seen state (atomic write)."""
    import json as _json
    from datetime import datetime as _datetime

    path = _project_seen_path(out_dir, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = _load_project_seen(out_dir, project_id)
    now = _datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    for link in links:
        key = _seen_key(link)
        seen[key] = {
            "status": str(link.status.value if hasattr(link.status, "value") else link.status),
            "at": now,
        }
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(_json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _write_radar_output(
    out_dir: str | Path,
    project_id: str,
    run_id: str,
    context,
    intents: list,
    queries: list,
    links: list[ProjectPaperLink],
) -> None:
    """Write radar run artifacts to the project's paper directory."""
    import json as _json
    from datetime import datetime

    base = Path(out_dir) / project_id / "papers"
    base.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    payload = {
        "run_id": run_id,
        "timestamp": timestamp,
        "project_id": project_id,
        "context": context.model_dump(),
        "intents": [i.model_dump() for i in intents],
        "queries": [q.model_dump() for q in queries],
        "links": [l.model_dump() for l in links],
        "link_count": len(links),
    }

    run_file = base / f"run_{run_id}.json"
    run_file.write_text(
        _json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    latest_file = base / "latest.json"
    latest_file.write_text(
        _json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
