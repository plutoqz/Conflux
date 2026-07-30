"""Generate SearchIntent objects from ProjectResearchContext.

Each intent maps to a concrete search need: core topic monitoring,
milestone support, blocker resolution, evidence gap filling, competitor
tracking, or dataset/metric discovery.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from conflux.core.p2_contracts import (
    ProjectResearchContext,
    SearchIntent,
    SearchIntentType,
)


def generate_search_intents(
    context: ProjectResearchContext,
    *,
    llm_model: Any = None,
    llm_review: bool = False,
) -> list[SearchIntent]:
    """Generate search intents from project context.

    Returns a deterministic baseline of intents derived directly from the
    context fields.  When ``llm_review=True``, an LLM pass can enrich the
    baseline with refined query_terms and expected_evidence_types.
    """
    intents: list[SearchIntent] = []

    # Core topic intent — always present
    if context.overall_goal:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.CORE_TOPIC,
            summary=f"Core topic: {context.overall_goal}",
            query_terms=context.research_questions[:3] or [context.overall_goal],
            expected_evidence=["method", "baseline", "background"],
            priority=90,
        ))

    # Research question intents
    for rq in context.research_questions:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.CORE_TOPIC,
            summary=f"RQ: {rq}",
            query_terms=[rq],
            expected_evidence=["method", "dataset", "background"],
            priority=80,
            source_refs=[f"research_question: {rq[:80]}"],
        ))

    # Milestone intents
    for ms_title in context.active_milestones:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.MILESTONE,
            summary=f"Milestone: {ms_title}",
            query_terms=[ms_title],
            expected_evidence=["method", "baseline", "metric"],
            priority=75,
            source_refs=[f"milestone: {ms_title}"],
        ))

    # Blocker intents (from risks)
    for risk in context.current_risks:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.BLOCKER,
            summary=f"Risk: {risk}",
            query_terms=[risk],
            expected_evidence=["counterexample", "method"],
            priority=85,
            source_refs=[f"risk: {risk}"],
        ))

    # Evidence gap intents
    for gap in context.evidence_gaps:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.EVIDENCE_GAP,
            summary=f"Gap: {gap.description}",
            query_terms=[gap.description],
            expected_evidence=["dataset", "baseline", "metric"],
            priority=70,
            source_refs=[f"evidence_gap: {gap.id}"],
        ))

    # Next-action intents
    for action in context.next_actions:
        intents.append(_make_intent(
            context=context,
            intent_type=SearchIntentType.MILESTONE,
            summary=f"Next action: {action}",
            query_terms=[action],
            expected_evidence=["method", "dataset", "baseline"],
            priority=65,
            source_refs=[f"next_action: {action}"],
        ))

    # Dataset/metric intent (always one for reproducibility)
    intents.append(_make_intent(
        context=context,
        intent_type=SearchIntentType.DATASET_METRIC,
        summary="Datasets and benchmarks for reproducible evaluation",
        query_terms=["benchmark", "dataset", "reproducibility", "evaluation"],
        expected_evidence=["dataset", "metric", "baseline"],
        priority=60,
    ))

    # Optional LLM enrichment
    if llm_review and llm_model:
        intents = _enrich_with_llm(intents, context, llm_model)

    # Deduplicate by id
    seen: set[str] = set()
    deduped: list[SearchIntent] = []
    for intent in intents:
        if intent.id not in seen:
            seen.add(intent.id)
            deduped.append(intent)
    return deduped


def _make_intent(
    context: ProjectResearchContext,
    intent_type: SearchIntentType,
    summary: str,
    query_terms: list[str],
    expected_evidence: list[str],
    priority: int,
    source_refs: list[str] | None = None,
) -> SearchIntent:
    """Create a SearchIntent with a deterministic id."""
    raw = json.dumps({
        "pid": context.project_id,
        "type": intent_type.value,
        "summary": summary,
        "cv": context.profile_version,
    }, ensure_ascii=False, sort_keys=True)
    intent_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    return SearchIntent(
        id=intent_id,
        project_id=context.project_id,
        type=intent_type,
        summary=summary,
        query_terms=query_terms,
        expected_evidence_types=expected_evidence,
        related_rq_ids=[],
        related_milestone_ids=[],
        related_risk_ids=[],
        priority=priority,
        source_refs=source_refs or [],
        context_version=context.profile_version,
        status="proposed",
    )


def _enrich_with_llm(
    intents: list[SearchIntent],
    context: ProjectResearchContext,
    llm_model: Any,
) -> list[SearchIntent]:
    """Use an LLM to refine query_terms and evidence types.  Stub — safe no-op."""
    # P2 file-mode phase: LLM enrichment is a future optimization.
    # The deterministic baseline is sufficient for acceptance.
    return intents
