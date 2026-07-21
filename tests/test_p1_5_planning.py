from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from conflux.research_generalization import (
    build_domain_map,
    classify_query_archetype,
    derive_research_strategy,
    merge_discovered_dimensions,
)
from conflux.research_protocol import DomainMap, QueryArchetype, ResearchDimension


ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "architecture" / "p1_5"
DATASET = yaml.safe_load(
    (ROOT / "data" / "p1_5_research_eval.yaml").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", DATASET, ids=lambda case: case["id"])
def test_dataset_queries_classify_to_the_declared_archetype(case: dict[str, object]) -> None:
    archetype = classify_query_archetype(str(case["query"]))

    assert archetype.type == case["archetype"]
    assert archetype.expected_research_actions
    assert archetype.required_synthesis_functions


def test_empty_domain_lexicon_still_builds_recorded_dimensions() -> None:
    payload = json.loads((FIXTURES / "planner_recordings.json").read_text(encoding="utf-8"))

    for recording in payload["recordings"]:
        assert recording["domain_lexicon"] == []
        archetype = QueryArchetype.from_dict(recording["query_archetype"])
        recorded = DomainMap.from_dict(recording["domain_map"])

        first = build_domain_map(
            recording["query"],
            archetype,
            discovered_dimensions=[item.to_dict() for item in recorded.dimensions],
            terminology=recording["domain_lexicon"],
            scope=recorded.scope,
        )
        second = build_domain_map(
            recording["query"],
            archetype,
            discovered_dimensions=[item.to_dict() for item in recorded.dimensions],
            terminology=recording["domain_lexicon"],
            scope=recorded.scope,
        )

        minimum = recording["expected"]["minimum_major_dimensions"]
        assert len(first.dimensions) >= minimum
        assert [item.id for item in first.dimensions] == [item.id for item in second.dimensions]
        assert {item.id for item in recorded.dimensions} <= {item.id for item in first.dimensions}
        assert first.terminology


def test_merge_discovered_dimensions_deduplicates_aliases_and_respects_bound() -> None:
    base = DomainMap(
        scope="fault tolerant event processing platform",
        dimensions=[
            ResearchDimension(
                id="recovery",
                name="Failure recovery",
                importance=0.9,
                questions_to_answer=["Which failures can be recovered?"],
            )
        ],
    )
    discoveries: list[ResearchDimension] = [
        ResearchDimension(
            id="recovery-alias",
            name="Failure recovery and reliability",
            importance=0.95,
            questions_to_answer=["What is the recovery point?"],
            terminology=["checkpoint recovery"],
        )
    ]
    discoveries.extend(
        ResearchDimension(
            id=f"dimension-{index}",
            name=f"Independent facet code-{index:04d}",
            inclusion_reason="first-pass evidence discovered an independent concern",
            importance=0.7,
        )
        for index in range(20)
    )

    merged = merge_discovered_dimensions(
        base,
        discoveries,
        query=base.scope,
        max_dimensions=15,
    )

    assert len(merged.dimensions) == 15
    recovery_dimensions = [
        item for item in merged.dimensions if item.id in {"recovery", "recovery-alias"}
    ]
    assert len(recovery_dimensions) == 1
    assert recovery_dimensions[0].id == "recovery"
    assert recovery_dimensions[0].importance == 0.95
    assert set(recovery_dimensions[0].questions_to_answer) == {
        "Which failures can be recovered?",
        "What is the recovery point?",
    }


@pytest.mark.parametrize(
    "archetype_name",
    [
        "method_survey",
        "state_and_trends",
        "limitations_and_challenges",
        "comparison",
        "causal_mechanism",
        "solution_design",
        "evidence_review",
        "general_exploration",
    ],
)
def test_research_strategy_preserves_breadth_first_planning(archetype_name: str) -> None:
    strategy = derive_research_strategy(QueryArchetype(type=archetype_name))

    assert strategy.primary_archetype == archetype_name
    assert strategy.breadth_first is True
    assert strategy.discovery_actions
    assert strategy.stop_policy == [
        "high_importance_dimensions_reach_coverage_target",
        "evidence_and_dimension_saturation",
        "explicit_evidence_scarcity",
        "run_budget_or_deadline_exhausted",
    ]
