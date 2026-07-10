"""Paper-to-knowledge-base ingestion policy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import IngestionDecision, PaperAnalysis, PaperRecord


@dataclass(frozen=True, slots=True)
class IngestionPolicyConfig:
    """Thresholds for deciding how a paper enters knowledge storage."""

    metadata_threshold: float = 0.32
    summary_threshold: float = 0.62
    full_text_threshold: float = 0.82
    allow_full_text: bool = False


DEFAULT_POLICY = IngestionPolicyConfig()


def decide_ingestion(
    paper: PaperRecord,
    analysis: PaperAnalysis,
    *,
    policy: IngestionPolicyConfig = DEFAULT_POLICY,
    pinned_ids: Iterable[str] = (),
) -> IngestionDecision:
    """Return an explicit ingestion decision for a paper analysis."""

    pinned = set(pinned_ids)
    score = max(0.0, min(1.0, analysis.relevance_score))

    if paper.id in pinned or analysis.paper_id in pinned:
        return IngestionDecision(
            paper_id=paper.id,
            action="pinned",
            reason="Paper was explicitly pinned by the user.",
            priority=100,
            metadata=_decision_metadata(analysis),
        )

    if analysis.reading_level == "skip" or score < policy.metadata_threshold:
        return IngestionDecision(
            paper_id=paper.id,
            action="skip",
            reason="Paper did not pass the metadata relevance threshold.",
            priority=0,
            metadata=_decision_metadata(analysis),
        )

    if (
        analysis.reading_level == "deep"
        and score >= policy.full_text_threshold
        and policy.allow_full_text
        and paper.pdf_url
    ):
        return IngestionDecision(
            paper_id=paper.id,
            action="full_text",
            reason="High relevance paper with available PDF and full-text ingestion enabled.",
            priority=90,
            metadata=_decision_metadata(analysis),
        )

    if analysis.reading_level == "deep" and score >= policy.summary_threshold:
        return IngestionDecision(
            paper_id=paper.id,
            action="summary_only",
            reason="High relevance paper selected for abstract and analysis indexing.",
            priority=80,
            metadata=_decision_metadata(analysis),
        )

    return IngestionDecision(
        paper_id=paper.id,
        action="metadata_only",
        reason="Moderately relevant paper retained as metadata only.",
        priority=40,
        metadata=_decision_metadata(analysis),
    )


def default_policy(*, allow_full_text: bool = False) -> IngestionPolicyConfig:
    """Create the default policy with an explicit full-text toggle."""

    return IngestionPolicyConfig(allow_full_text=allow_full_text)


def _decision_metadata(analysis: PaperAnalysis) -> dict:
    return {
        "relevance_score": analysis.relevance_score,
        "reading_level": analysis.reading_level,
        "citation_value": analysis.citation_value,
    }
