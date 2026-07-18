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
    llm_review: bool = False,
    review_model=None,
) -> PaperInboxResult:
    """Run the paper radar pipeline from an offline fixture."""

    profile = load_profile(profile_path)
    loaded = load_paper_fixture(fixture_path)
    return build_inbox(profile, loaded, out_dir=out_dir, llm_review=llm_review, review_model=review_model)


def build_inbox_from_arxiv(
    profile_path: str | Path,
    *,
    max_results: int = 10,
    out_dir: str | Path | None = None,
    llm_review: bool = False,
    review_model=None,
) -> PaperInboxResult:
    """Run the paper radar pipeline from real arXiv search."""

    profile = load_profile(profile_path)
    papers = []
    for query in profile_arxiv_queries(profile):
        papers.extend(search_arxiv(query, max_results=max_results))
    return build_inbox(profile, papers, out_dir=out_dir, llm_review=llm_review, review_model=review_model)


def build_inbox(
    profile: ResearchProfile,
    papers: list[PaperRecord],
    *,
    out_dir: str | Path | None = None,
    llm_review: bool = False,
    review_model=None,
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
    if llm_review:
        _apply_llm_review(analyzed, profile, review_model=review_model, stats=stats)
    artifacts = write_inbox_artifacts(profile, analyzed, out_dir=out_dir, stats=stats) if out_dir else None
    return PaperInboxResult(profile=profile, analyzed=analyzed, stats=stats, artifacts=artifacts)


def _apply_llm_review(analyzed, profile: ResearchProfile, *, review_model=None, stats: dict) -> None:
    """Apply semantic review while preserving deterministic candidates on failure."""

    from conflux.builtin.paper.plugin import paper_review
    from conflux.sdk.testing import make_plugin_context

    import hashlib
    import json

    profile_version = hashlib.sha256(
        json.dumps(profile.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    ctx = make_plugin_context(model=review_model, config={"model_preset": "cheap"})
    result = paper_review(
        ctx,
        papers=[paper.to_dict() for paper, _ in analyzed],
        profile_id=profile.id,
        profile_version=profile_version,
        profile_keywords=profile.keywords,
        profile_questions=profile.research_questions,
        profile_fields=profile.fields,
    )
    reviews = {str(item.get("paper_id")): item for item in result.output.get("reviews") or []}
    relevance_weight = {"relevant": 0.9, "partially_relevant": 0.6, "irrelevant": 0.1}
    reviewed_count = 0
    unreviewed_count = 0
    deep_review_failures = 0
    for paper, analysis in analyzed:
        deterministic_score = float(analysis.relevance_score)
        review = reviews.get(paper.id)
        if not review or review.get("relevance") == "unreviewed":
            unreviewed_count += 1
            analysis.metadata["review_status"] = "unreviewed"
            analysis.metadata["candidate_status"] = str(
                (review or {}).get("candidate_status") or "provisional"
            )
            analysis.metadata["deterministic_score"] = deterministic_score
            analysis.metadata["semantic_score"] = None
            analysis.metadata["review_error_code"] = str(
                (review or {}).get("error_code") or "llm_unavailable"
            )
            analysis.metadata["review_error"] = str(
                (review or {}).get("error_detail")
                or result.error
                or "LLM semantic review was not completed."
            )
            analysis.metadata["review_next_action"] = str(
                review.get("next_action") if review else result.output.get("next_action")
                or "Configure a working review model and retry unreviewed papers."
            )
            continue
        relevance = str(review.get("relevance") or "irrelevant")
        confidence = max(0.0, min(1.0, float(review.get("confidence") or 0.0)))
        reviewed_count += 1
        analysis.metadata["llm_review"] = review
        analysis.metadata["review_status"] = str(review.get("review_status") or "reviewed")
        analysis.metadata["candidate_status"] = str(review.get("candidate_status") or "reviewed")
        analysis.metadata["deterministic_score"] = deterministic_score
        semantic_score = review.get("semantic_score")
        try:
            semantic_score = float(semantic_score)
        except (TypeError, ValueError):
            semantic_score = relevance_weight.get(relevance, 0.0) * confidence
        semantic_score = round(max(0.0, min(1.0, semantic_score)), 3)
        analysis.metadata["semantic_score"] = semantic_score
        if review.get("deep_review_status") == "unreviewed":
            deep_review_failures += 1
            analysis.metadata["deep_review_error_code"] = str(review.get("deep_error_code") or "")
            analysis.metadata["deep_review_error"] = str(review.get("deep_error_detail") or "")
        analysis.relevance_score = semantic_score
        analysis.reading_level = (
            "deep" if relevance == "relevant" and confidence >= 0.75
            else "skim" if relevance in {"relevant", "partially_relevant"}
            else "skip"
        )  # type: ignore[assignment]
    stats.update({
        "review_status": result.status.value,
        "reviewed": reviewed_count,
        "unreviewed": unreviewed_count,
        "review_batch_size": 4,
        "review_batches": (len(analyzed) + 3) // 4,
        "deep_review_failures": deep_review_failures,
        "review_next_action": str(result.output.get("next_action") or ""),
    })
