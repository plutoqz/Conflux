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
    EvidenceUtility,
    PaperIdentity,
    PaperLinkStatus,
    PaperSource,
    ProjectPaperLink,
    ProjectResearchConfig,
    RadarRunResult,
    RadarRunStats,
)
from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_ingestion.scorer import score_papers
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
    )


def run_paper_radar(
    project: ProjectDefinition,
    profile: ResearchProfile,
    *,
    audit: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
    llm_review: bool = False,
    review_model: Any = None,
) -> RadarRunResult:
    """Run the full P2 paper radar pipeline for a project.

    Steps:
    1. Build ProjectResearchContext from project + profile + audit
    2. Generate SearchIntent list
    3. Resolve QuerySpec list from profile tracks (or fallback)
    4. Execute queries against paper sources
    5. De-duplicate, filter, create ProjectPaperLink entries
    6. Produce RadarRunResult
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

    # Step 3: Resolve query specs
    queries = resolve_query_specs_from_profile(profile, config=config, context=context)

    # Stats are created up-front so query execution and deep analysis can
    # record telemetry (query-level results, LLM calls, tokens).
    stats = RadarRunStats(
        project_id=project.id,
        run_id=run_id,
        started_at=__import__("datetime").datetime.utcnow(),
    )

    # Step 4: Execute queries against sources
    all_papers, failed_sources = _execute_queries(queries, stats=stats)

    # Step 5: De-duplicate and filter
    unique_papers = _deduplicate_papers(all_papers)
    filtered_papers = _apply_negative_filters(unique_papers, profile)
    ranked = score_papers(filtered_papers, profile)[:config.max_candidates]
    ranked_papers = [paper for paper, _ in ranked]
    score_by_id = {paper.id: score.score for paper, score in ranked}
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
    project_seen = _load_project_seen(out_dir, project.id) if out_dir else {}
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
        if stats.needs_review_paper_ids:
            needs_review_ids = set(stats.needs_review_paper_ids)
            for link in links:
                if link.paper_identity.canonical_id in needs_review_ids:
                    link.status = PaperLinkStatus.NEEDS_REVIEW
            stats.needs_review = len(needs_review_ids)
        stats.skipped_seen_rejected = skipped_seen_rejected

    # Write output if out_dir specified
    if out_dir:
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
    return ProjectResearchConfig(
        profile=raw.get("profile", f"profiles/{profile.id}.yaml"),
        sources=_parse_sources(raw.get("sources", ["arxiv", "semantic_scholar"])),
        cadence=raw.get("cadence", "manual"),
        max_candidates=int(raw.get("max_candidates", 100)),
        deep_read_limit=int(raw.get("deep_read_limit", 5)),
        auto_generate_queries=bool(raw.get("auto_generate_queries", True)),
        require_query_review=bool(raw.get("require_query_review", True)),
        require_plan_writeback_approval=bool(raw.get("require_plan_writeback_approval", True)),
        track_overrides=list(raw.get("track_overrides") or []),
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
) -> tuple[list[PaperRecord], list[str]]:
    """Execute QuerySpec objects against their paper sources.

    Returns (all_papers, failed_sources).
    Falls back gracefully when a source is unavailable.  When ``stats`` is
    provided, per-query results are recorded for query-level reporting.
    """
    import logging

    from conflux.paper_ingestion.arxiv_source import search_arxiv
    from conflux.paper_ingestion.semantic_scholar_source import search_semantic_scholar

    logger = logging.getLogger(__name__)
    all_papers: list[PaperRecord] = []
    failed: set[str] = set()
    per_query: list[dict[str, Any]] = []

    for spec in queries:
        query_id = str(spec.id or "")
        entry: dict[str, Any] = {
            "query_id": query_id,
            "track_id": str(spec.track_id or ""),
            "source": str(spec.source.value if hasattr(spec.source, "value") else spec.source),
            "candidate_count": 0,
            "failed": False,
        }
        try:
            if spec.source == PaperSource.ARXIV:
                papers = search_arxiv(spec.query, max_results=spec.max_results)
            elif spec.source == PaperSource.SEMANTIC_SCHOLAR:
                papers = search_semantic_scholar(
                    spec.query,
                    max_results=spec.max_results,
                )
            else:
                logger.warning("Unknown source: %s", spec.source)
                failed.add(str(spec.source.value))
                entry["failed"] = True
                per_query.append(entry)
                continue
            entry["candidate_count"] = len(papers)
            all_papers.extend(papers)
        except Exception:
            failed.add(spec.source.value)
            entry["failed"] = True
        per_query.append(entry)

    if stats is not None:
        stats.query_stats = per_query
    return all_papers, sorted(failed)


def _deduplicate_papers(papers: list[PaperRecord]) -> list[PaperRecord]:
    """De-duplicate paper records by DOI and title."""
    from conflux.paper_ingestion.dedup import deduplicate_papers
    return deduplicate_papers(papers)


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
