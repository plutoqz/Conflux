"""Filtering helpers for paper ingestion."""

from __future__ import annotations

from conflux.research_profile import ResearchProfile

from .models import PaperRecord


def apply_negative_filters(papers: list[PaperRecord], profile: ResearchProfile) -> list[PaperRecord]:
    """Remove papers that match profile-level negative keywords."""

    return [paper for paper in papers if not paper_matches_negative_filter(paper, profile)]


def paper_matches_negative_filter(paper: PaperRecord, profile: ResearchProfile) -> bool:
    """Return whether a paper should be excluded by profile-level negative terms."""

    text = f"{paper.title}\n{paper.abstract}".casefold()
    return any(
        term.casefold() in text
        for term in profile.negative_keywords
        if term.strip()
    )
