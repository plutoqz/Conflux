"""Filtering helpers for paper ingestion."""

from __future__ import annotations

from conflux.research_profile import ResearchProfile

from .models import PaperRecord


def apply_negative_filters(papers: list[PaperRecord], profile: ResearchProfile) -> list[PaperRecord]:
    """Remove papers that match profile-level negative keywords."""

    negative = [item.lower() for item in profile.negative_keywords if item.strip()]
    if not negative:
        return papers

    kept = []
    for paper in papers:
        text = f"{paper.title}\n{paper.abstract}".lower()
        if any(term in text for term in negative):
            continue
        kept.append(paper)
    return kept
