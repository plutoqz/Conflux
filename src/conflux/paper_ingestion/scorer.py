"""Deterministic paper relevance scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from conflux.research_profile import ResearchProfile

from .models import PaperRecord


@dataclass(slots=True)
class PaperScore:
    """A deterministic relevance score with transparent matching reasons."""

    paper_id: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    matched_questions: list[str] = field(default_factory=list)
    matched_venues: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "matched_questions": self.matched_questions,
            "matched_venues": self.matched_venues,
            "matched_fields": self.matched_fields,
            "reasons": self.reasons,
        }


def score_paper(paper: PaperRecord, profile: ResearchProfile) -> PaperScore:
    """Score one paper against a profile using deterministic lexical signals."""

    text = _paper_text(paper)
    matched_keywords = _matched_terms(profile.keywords, text)
    matched_fields = _matched_terms(profile.fields, text)
    matched_venues = _matched_terms(profile.target_venues, f"{paper.venue} {' '.join(paper.categories)}")
    matched_questions = _matched_questions(profile.research_questions, text)

    keyword_score = _coverage(matched_keywords, profile.keywords)
    field_score = _coverage(matched_fields, profile.fields)
    question_score = min(1.0, len(matched_questions) / max(1, len(profile.research_questions)))
    venue_score = min(1.0, len(matched_venues) / 2)
    metadata_score = 0.0
    if paper.pdf_url:
        metadata_score += 0.05
    if paper.published_at:
        metadata_score += 0.05
    if paper.authors:
        metadata_score += 0.03

    score = (
        0.45 * keyword_score
        + 0.20 * question_score
        + 0.15 * field_score
        + 0.10 * venue_score
        + metadata_score
    )
    if len(matched_keywords) >= 2:
        score += 0.10
    if matched_questions and matched_keywords:
        score += 0.08

    score = round(max(0.0, min(1.0, score)), 3)
    reasons = []
    if matched_keywords:
        reasons.append(f"matched keywords: {', '.join(matched_keywords[:5])}")
    if matched_questions:
        reasons.append(f"matched research questions: {len(matched_questions)}")
    if matched_fields:
        reasons.append(f"matched fields: {', '.join(matched_fields[:3])}")
    if matched_venues:
        reasons.append(f"matched target venue/category: {', '.join(matched_venues[:3])}")
    if paper.pdf_url:
        reasons.append("has PDF URL")
    if not reasons:
        reasons.append("no strong profile match")

    return PaperScore(
        paper_id=paper.id,
        score=score,
        matched_keywords=matched_keywords,
        matched_questions=matched_questions,
        matched_venues=matched_venues,
        matched_fields=matched_fields,
        reasons=reasons,
    )


def score_papers(papers: list[PaperRecord], profile: ResearchProfile) -> list[tuple[PaperRecord, PaperScore]]:
    """Score and sort papers by descending relevance."""

    scored = [(paper, score_paper(paper, profile)) for paper in papers]
    return sorted(scored, key=lambda item: (item[1].score, item[0].published_at is not None), reverse=True)


def reading_level_for_score(score: float) -> str:
    """Map a relevance score to a reading level."""

    if score >= 0.62:
        return "deep"
    if score >= 0.32:
        return "skim"
    return "skip"


def _paper_text(paper: PaperRecord) -> str:
    return " ".join([
        paper.title,
        paper.abstract,
        paper.venue,
        " ".join(paper.categories),
    ]).lower()


def _matched_terms(terms: list[str], text: str) -> list[str]:
    matches = []
    lowered = text.lower()
    for term in terms:
        normalized = " ".join(term.lower().split())
        if not normalized:
            continue
        if normalized in lowered:
            matches.append(term)
            continue
        tokens = _tokens(normalized)
        if tokens and sum(1 for token in tokens if token in lowered) / len(tokens) >= 0.67:
            matches.append(term)
    return _dedupe(matches)


def _matched_questions(questions: list[str], text: str) -> list[str]:
    matches = []
    for question in questions:
        tokens = [token for token in _tokens(question.lower()) if len(token) >= 5]
        if not tokens:
            continue
        overlap = sum(1 for token in tokens if token in text)
        if overlap / len(tokens) >= 0.25:
            matches.append(question)
    return matches


def _coverage(matches: list[str], terms: list[str]) -> float:
    if not terms:
        return 0.0
    return min(1.0, len(matches) / max(1, min(len(terms), 6)))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9_.-]{2,}", text.lower())


def _dedupe(values: list[str]) -> list[str]:
    clean = []
    seen = set()
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            clean.append(value)
    return clean
