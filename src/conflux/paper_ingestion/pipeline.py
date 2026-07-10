"""Paper radar pipeline for offline and real source inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from conflux.research_profile import ResearchProfile, load_profile

from .analyzer import analyze_papers
from .arxiv_source import profile_arxiv_queries, search_arxiv
from .dedup import deduplicate_papers
from .filters import apply_negative_filters
from .fixtures import load_paper_fixture
from .inbox_report import InboxArtifacts, write_inbox_artifacts
from .models import PaperAnalysis, PaperRecord


@dataclass(slots=True)
class PaperInboxResult:
    profile: ResearchProfile
    analyzed: list[tuple[PaperRecord, PaperAnalysis]]
    stats: dict
    artifacts: InboxArtifacts | None = None


def build_inbox_from_fixture(
    profile_path: str | Path,
    fixture_path: str | Path,
    *,
    out_dir: str | Path | None = None,
) -> PaperInboxResult:
    """Run the paper radar pipeline from an offline fixture."""

    profile = load_profile(profile_path)
    loaded = load_paper_fixture(fixture_path)
    return build_inbox(profile, loaded, out_dir=out_dir)


def build_inbox_from_arxiv(
    profile_path: str | Path,
    *,
    max_results: int = 10,
    out_dir: str | Path | None = None,
) -> PaperInboxResult:
    """Run the paper radar pipeline from real arXiv search."""

    profile = load_profile(profile_path)
    papers = []
    for query in profile_arxiv_queries(profile):
        papers.extend(search_arxiv(query, max_results=max_results))
    return build_inbox(profile, papers, out_dir=out_dir)


def build_inbox(
    profile: ResearchProfile,
    papers: list[PaperRecord],
    *,
    out_dir: str | Path | None = None,
) -> PaperInboxResult:
    """Deduplicate, filter, analyze, and optionally write inbox artifacts."""

    unique = deduplicate_papers(papers)
    filtered = apply_negative_filters(unique, profile)
    analyzed = analyze_papers(filtered, profile)
    stats = {
        "total_loaded": len(papers),
        "after_dedup": len(unique),
        "after_filter": len(filtered),
        "deep": sum(1 for _, analysis in analyzed if analysis.reading_level == "deep"),
        "skim": sum(1 for _, analysis in analyzed if analysis.reading_level == "skim"),
        "skip": sum(1 for _, analysis in analyzed if analysis.reading_level == "skip"),
    }
    artifacts = write_inbox_artifacts(profile, analyzed, out_dir=out_dir, stats=stats) if out_dir else None
    return PaperInboxResult(profile=profile, analyzed=analyzed, stats=stats, artifacts=artifacts)
