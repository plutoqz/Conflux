"""Offline paper analysis derived from deterministic relevance scores."""

from __future__ import annotations

from conflux.research_profile import ResearchProfile

from .models import PaperAnalysis, PaperRecord
from .scorer import PaperScore, reading_level_for_score, score_papers


def analyze_paper(paper: PaperRecord, score: PaperScore, profile: ResearchProfile) -> PaperAnalysis:
    """Create a lightweight analysis record without LLM calls."""

    reading_level = reading_level_for_score(score.score)
    citation_value = "high" if reading_level == "deep" else "medium" if reading_level == "skim" else "low"
    method_summary = _method_summary(paper)
    novelty = _novelty_hint(paper, score)
    limitations = _limitations(paper, score)

    return PaperAnalysis(
        paper_id=paper.id,
        relevance_score=score.score,
        reading_level=reading_level,  # type: ignore[arg-type]
        matched_questions=score.matched_questions,
        method_summary=method_summary,
        novelty=novelty,
        reusable_methods=score.matched_keywords[:5],
        reusable_datasets=[],
        citation_value=citation_value,  # type: ignore[arg-type]
        limitations=limitations,
        metadata={
            "matched_keywords": score.matched_keywords,
            "matched_fields": score.matched_fields,
            "matched_venues": score.matched_venues,
            "score_reasons": score.reasons,
            "profile_id": profile.id,
        },
    )


def analyze_papers(papers: list[PaperRecord], profile: ResearchProfile) -> list[tuple[PaperRecord, PaperAnalysis]]:
    """Score and analyze papers with a deterministic offline path."""

    return [
        (paper, analyze_paper(paper, score, profile))
        for paper, score in score_papers(papers, profile)
    ]


def _method_summary(paper: PaperRecord) -> str:
    text = paper.abstract.strip() or paper.title.strip()
    if not text:
        return "No method summary available."
    return text[:280]


def _novelty_hint(paper: PaperRecord, score: PaperScore) -> str:
    if score.matched_keywords:
        return f"Potentially relevant to {', '.join(score.matched_keywords[:3])}."
    if paper.categories:
        return f"Potentially relevant by category: {', '.join(paper.categories[:3])}."
    return "Novelty not assessed in offline mode."


def _limitations(paper: PaperRecord, score: PaperScore) -> str:
    notes = []
    if not paper.pdf_url:
        notes.append("No PDF URL available.")
    if not score.matched_questions:
        notes.append("No direct research-question match.")
    if score.score < 0.32:
        notes.append("Low profile relevance.")
    return " ".join(notes) if notes else "Offline analysis only; no LLM deep reading yet."
