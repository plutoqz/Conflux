from __future__ import annotations

import json
from pathlib import Path

import pytest

from conflux.research_protocol import (
    CoverageDimension,
    CoverageMatrix,
    DomainMap,
    DynamicResearchBudget,
    QueryArchetype,
    ReportOutline,
    ResearchDimension,
    ResearchStrategy,
    SectionClaim,
    SectionContract,
    SectionDraft,
    SourcePlan,
)


FIXTURES = Path(__file__).parent / "fixtures" / "architecture" / "p1_5"


PROTOCOL_VALUES = [
    QueryArchetype(
        type="comparison",
        confidence=0.91,
        user_intent="compare two deployment options",
        expected_research_actions=["identify_comparison_axes", "compare_evidence"],
        required_synthesis_functions=["comparative_synthesis"],
        secondary_types=["limitations_and_challenges"],
        selection_reason="comparison language is explicit",
    ),
    ResearchStrategy(
        primary_archetype="comparison",
        secondary_archetypes=["limitations_and_challenges"],
        rationale="compare evidence before selecting an option",
        discovery_actions=["identify_comparison_axes"],
        depth_actions=["compare_evidence"],
        required_synthesis_functions=["comparative_synthesis"],
        stop_policy=["evidence_and_dimension_saturation"],
        breadth_first=True,
    ),
    ResearchDimension(
        id="reliability",
        name="Failure recovery and reliability",
        inclusion_reason="operational constraint",
        child_ids=["recovery-time"],
        questions_to_answer=["Which failures are recoverable?"],
        expected_evidence_types=["technical_documentation"],
        importance=0.95,
        current_coverage="partial",
        conflicts=["recovery guarantees differ"],
        gaps=["independent recovery test"],
        stop_conditions=["two independent sources"],
        terminology=["recovery point objective"],
    ),
    DomainMap(
        scope="compare operational approaches",
        key_concepts=["recovery", "auditability"],
        terminology=["recovery point objective"],
        dimensions=[
            ResearchDimension(id="reliability", name="Reliability", importance=0.95),
            ResearchDimension(id="governance", name="Governance", importance=0.8),
        ],
        dimension_relations=[
            {"from": "reliability", "to": "governance", "relation": "constrains"}
        ],
        disputed_boundaries=["shared-responsibility boundary"],
        discovery_sources=["model_prior", "first_pass_evidence"],
    ),
    CoverageDimension(
        dimension_id="reliability",
        status="conflicting",
        body_evidence=True,
        covered_actions=["compare_evidence"],
        missing_actions=["identify_tradeoffs"],
        high_authority_source=True,
        independent_source_count=2,
        cross_validation_required=True,
        conflicts=["recovery guarantees differ"],
        temporal_conflicts=["version scope changed"],
        terminology_ambiguities=["checkpoint"],
        model_only=False,
        evidence_ids=["e-1", "e-2"],
        source_ids=["source-a", "source-b"],
        evidence_count=2,
        saturation=0.72,
        gap_summary=["resolve the version boundary"],
    ),
    CoverageMatrix(
        dimensions=[
            CoverageDimension(
                dimension_id="reliability",
                status="covered",
                body_evidence=True,
                evidence_ids=["e-1"],
                source_ids=["source-a"],
                evidence_count=1,
                saturation=0.9,
            )
        ],
        iteration=2,
        overall_coverage=0.84,
        high_importance_coverage=0.91,
        saturation=0.8,
        stop_reason="coverage_and_saturation_reached",
        exhausted=False,
    ),
    DynamicResearchBudget(
        depth="deep",
        complexity_score=0.82,
        major_dimension_limit=12,
        breadth_query_limit=24,
        depth_query_limit=18,
        evidence_limit=32,
        web_fetch_limit=8,
        web_fetch_attempts=16,
        max_gap_iterations=3,
        per_dimension_min_queries=1,
        per_dimension_min_evidence=2,
        section_length_budgets={"reliability": 900},
        total_output_chars=14000,
        token_budget=140000,
        timeout_seconds=480,
        global_hard_limits={"major_dimension_limit": 15},
    ),
    SourcePlan(
        id="source-plan-1",
        dimension_id="reliability",
        evidence_needs=["benchmark", "technical_documentation"],
        source_types=["technical_documentation", "model_knowledge"],
        source_ids=["builtin.web", "builtin.model"],
        query_intents=["find recovery guarantees"],
        recency_requirement="current",
        authority_threshold=0.8,
        cross_check_required=True,
        budget={"queries": 2, "evidence": 4, "web_fetches": 2},
        fallback_order=["builtin.rag", "builtin.model"],
        model_role="analysis_and_query_expansion",
    ),
    SectionClaim(
        id="claim-1",
        text="The recovery guarantees differ by failure mode.",
        claim_type="external_fact",
        evidence_ids=["e-1"],
        citation_refs=["[1]"],
        confidence=0.88,
        limitations=["single implementation version"],
        relationship="supports",
        externally_supported=True,
    ),
    SectionDraft(
        section_id="section-reliability",
        title="Recovery and reliability",
        dimension_ids=["reliability"],
        research_questions=["Which failures are recoverable?"],
        claims=[
            SectionClaim(
                id="claim-1",
                text="Checkpoint recovery is documented.",
                evidence_ids=["e-1"],
                citation_refs=["[1]"],
                externally_supported=True,
            )
        ],
        content="Evidence supports checkpoint recovery for the documented failure mode.",
        coverage_status="partial",
        conflicts=[],
        unresolved_gaps=["independent evidence for target B"],
        suggested_length=700,
        synthesis_priority=0.9,
        verified=False,
    ),
    SectionContract(
        id="section-reliability",
        title="Recovery and reliability",
        function="dimension_analysis",
        dimension_ids=["reliability"],
        questions_to_answer=["Which failures are recoverable?"],
        required_claim_types=["external_fact", "limitation"],
        evidence_requirements=["independent recovery evidence"],
        comparison_axes=["recovery point", "manual intervention"],
        dependencies=[],
        coverage_target=0.85,
        length_budget=700,
    ),
    ReportOutline(
        query_archetype="comparison",
        audience="technical decision maker",
        scope="operational comparison",
        answer_strategy="compare by shared axes",
        sections=[
            SectionContract(
                id="section-reliability",
                title="Recovery and reliability",
                function="dimension_analysis",
                dimension_ids=["reliability"],
            )
        ],
        cross_section_synthesis=["tradeoffs", "unresolved_conflicts"],
        citation_policy="numeric citations resolve to body evidence",
        reliability_policy="disclose incomplete dimensions",
    ),
]


@pytest.mark.parametrize(
    "value",
    PROTOCOL_VALUES,
    ids=lambda value: type(value).__name__,
)
def test_p1_5_protocols_round_trip_through_json(value: object) -> None:
    payload = json.loads(json.dumps(value.to_dict()))

    restored = type(value).from_dict(payload)

    assert restored.to_dict() == payload


def test_invalid_archetype_falls_back_to_general_exploration() -> None:
    archetype = QueryArchetype.from_dict(
        {
            "type": "domain_specific_magic_template",
            "confidence": 4,
            "user_intent": "explore the question",
        }
    )

    assert archetype.type == "general_exploration"
    assert archetype.confidence == 1.0


def test_report_fixture_protocols_preserve_traceability_ids() -> None:
    payload = json.loads((FIXTURES / "report_traceability.json").read_text(encoding="utf-8"))
    domain_map = DomainMap.from_dict(payload["domain_map"])
    coverage = CoverageMatrix.from_dict(payload["coverage_matrix"])
    contracts = [
        SectionContract.from_dict(item, index=index)
        for index, item in enumerate(payload["section_contracts"])
    ]
    outline = ReportOutline.from_dict(
        {
            **payload["report_outline"],
            "sections": [contract.to_dict() for contract in contracts],
        }
    )
    drafts = [SectionDraft.from_dict(item) for item in payload["section_drafts"]]

    dimension_ids = [dimension.id for dimension in domain_map.dimensions]
    contract_ids = [contract.id for contract in contracts]
    assert list(coverage.by_dimension()) == dimension_ids
    assert contract_ids == payload["report_outline"]["sections"]
    assert [section.id for section in outline.sections] == contract_ids
    assert [draft.section_id for draft in drafts] == contract_ids

    round_tripped = ReportOutline.from_dict(json.loads(json.dumps(outline.to_dict())))
    assert [section.id for section in round_tripped.sections] == contract_ids


@pytest.mark.parametrize(
    ("factory", "payload", "index", "expected_id"),
    [
        (ResearchDimension, {"name": "A dimension"}, 2, "dim-3"),
        (SourcePlan, {"dimension_id": "dimension-a"}, 2, "source-plan-3"),
        (SectionClaim, {"text": "A claim"}, 2, "section-claim-3"),
        (SectionContract, {"title": "A section"}, 2, "section-3"),
    ],
)
def test_index_generated_protocol_ids_are_stable(
    factory: type[object], payload: dict[str, object], index: int, expected_id: str
) -> None:
    first = factory.from_dict(payload, index=index)
    second = factory.from_dict(payload, index=index)

    assert first.id == expected_id
    assert second.id == expected_id
