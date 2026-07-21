from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conflux.research_generalization import (
    allocate_dynamic_budget,
    build_coverage_matrix,
    build_source_plans,
    prioritize_coverage_gaps,
    research_should_stop,
)
from conflux.research_protocol import (
    CoverageDimension,
    CoverageMatrix,
    DomainMap,
    DynamicResearchBudget,
    QueryArchetype,
    ResearchDimension,
)


FIXTURES = Path(__file__).parent / "fixtures" / "architecture" / "p1_5"


def _domain_map(count: int, *, scope: str, importance: float = 0.8) -> DomainMap:
    return DomainMap(
        scope=scope,
        dimensions=[
            ResearchDimension(
                id=f"dimension-{index}",
                name=f"Research dimension {index}",
                importance=importance,
                expected_evidence_types=["technical_documentation"],
                questions_to_answer=[f"What evidence covers dimension {index}?"],
            )
            for index in range(count)
        ],
    )


def _comparison_archetype() -> QueryArchetype:
    return QueryArchetype(
        type="comparison",
        expected_research_actions=[
            "identify_comparison_axes",
            "compare_evidence",
            "identify_tradeoffs",
        ],
        required_synthesis_functions=["comparative_synthesis", "tradeoff_synthesis"],
    )


def test_broad_deep_budget_expands_beyond_narrow_without_breaking_hard_caps() -> None:
    fixture = json.loads((FIXTURES / "budget_cases.json").read_text(encoding="utf-8"))
    narrow_case = next(item for item in fixture["cases"] if item["id"] == "narrow_stable_healthy")
    broad_query = (
        "Compare the complete current landscape of major approaches across performance, "
        "reliability, cost, governance, implementation, and unresolved challenges."
    )
    narrow_query = "What is one rollback method?"
    hard_limits = {
        "max_dimensions": 12,
        "max_evidence": 30,
        "max_gap_iterations": 2,
        "web_fetch_limit": 8,
        "web_fetch_attempts": 16,
        "max_output_chars": 12000,
    }

    narrow = allocate_dynamic_budget(
        "deep",
        narrow_query,
        _comparison_archetype(),
        _domain_map(3, scope=narrow_query),
        source_health={"RAG": "success", "Web": "success"},
        hard_limits=hard_limits,
    )
    broad = allocate_dynamic_budget(
        "deep",
        broad_query,
        _comparison_archetype(),
        _domain_map(11, scope=broad_query),
        source_health={"RAG": "no_evidence", "Web": "success"},
        hard_limits=hard_limits,
    )

    assert narrow.major_dimension_limit <= narrow_case["expected"]["max_dimensions"]
    assert broad.major_dimension_limit > narrow.major_dimension_limit
    assert broad.evidence_limit > narrow.evidence_limit
    assert broad.breadth_query_limit > narrow.breadth_query_limit
    assert broad.total_output_chars > narrow.total_output_chars
    assert broad.major_dimension_limit <= hard_limits["max_dimensions"]
    assert broad.evidence_limit <= hard_limits["max_evidence"]
    assert broad.max_gap_iterations <= hard_limits["max_gap_iterations"]
    assert broad.web_fetch_limit <= hard_limits["web_fetch_limit"]
    assert broad.web_fetch_attempts <= hard_limits["web_fetch_attempts"]
    assert broad.total_output_chars <= hard_limits["max_output_chars"]


def test_quick_budget_remains_below_deep_for_the_same_broad_question() -> None:
    query = (
        "Survey the complete landscape of current approaches, mechanisms, implementations, "
        "limitations, evidence quality, and open questions."
    )
    domain_map = _domain_map(10, scope=query)
    archetype = _comparison_archetype()

    quick = allocate_dynamic_budget("quick", query, archetype, domain_map)
    deep = allocate_dynamic_budget("deep", query, archetype, domain_map)

    for field in (
        "major_dimension_limit",
        "breadth_query_limit",
        "depth_query_limit",
        "evidence_limit",
        "web_fetch_limit",
        "web_fetch_attempts",
        "max_gap_iterations",
        "total_output_chars",
        "token_budget",
        "timeout_seconds",
    ):
        assert getattr(quick, field) < getattr(deep, field), field


def test_rag_absence_shifts_retrieval_capacity_toward_web() -> None:
    query = "Survey the complete current landscape and all major implementation dimensions."
    domain_map = _domain_map(10, scope=query)
    archetype = _comparison_archetype()

    healthy = allocate_dynamic_budget(
        "deep",
        query,
        archetype,
        domain_map,
        source_health={"RAG": "success", "Web": "success"},
    )
    rag_empty = allocate_dynamic_budget(
        "deep",
        query,
        archetype,
        domain_map,
        source_health={"RAG": "no_evidence", "Web": "success"},
    )

    assert rag_empty.web_fetch_limit >= healthy.web_fetch_limit
    assert rag_empty.web_fetch_attempts >= healthy.web_fetch_attempts
    assert (
        rag_empty.web_fetch_limit > healthy.web_fetch_limit
        or rag_empty.web_fetch_attempts > healthy.web_fetch_attempts
    )


def test_global_schedule_caps_cross_source_queries_and_reserves_web_gap_budget() -> None:
    from conflux.graph_p15 import (
        _breadth_web_limits,
        _budgeted_source_tasks,
        _record_schedule_usage,
        _runtime_budget_quality,
    )

    query = "Survey the complete implementation landscape and unresolved gaps."
    budget = DynamicResearchBudget(
        breadth_query_limit=5,
        depth_query_limit=4,
        web_fetch_limit=3,
        web_fetch_attempts=5,
        max_gap_iterations=1,
    )
    plans = build_source_plans(
        _domain_map(5, scope=query),
        _comparison_archetype(),
        source_health={"RAG": "no_evidence", "Web": "success"},
        budget=budget,
    )

    assert sum(item.budget["queries"] for item in plans) <= budget.breadth_query_limit
    assert sum(item.budget["web_fetches"] for item in plans) <= budget.web_fetch_limit

    usage: dict[str, object] = {}
    breadth_fetches, breadth_attempts = _breadth_web_limits(budget, usage)
    assert breadth_fetches == 2
    scheduled = _budgeted_source_tasks(
        [item.to_dict() for item in plans],
        query_limit=budget.breadth_query_limit,
        web_fetch_limit=breadth_fetches,
        web_fetch_attempts=breadth_attempts,
    )
    usage = _record_schedule_usage(usage, scheduled, phase="breadth")

    assert len(scheduled["RAG"]) + len(scheduled["Web"]) <= budget.breadth_query_limit
    assert usage["web_fetches"] == 2
    assert usage["web_fetch_attempts"] <= breadth_attempts

    depth = _budgeted_source_tasks(
        [item.to_dict() for item in plans],
        query_limit=budget.depth_query_limit,
        web_fetch_limit=budget.web_fetch_limit - int(usage["web_fetches"]),
        web_fetch_attempts=budget.web_fetch_attempts - int(usage["web_fetch_attempts"]),
    )
    usage = _record_schedule_usage(usage, depth, phase="depth")
    usage["gap_iterations"] = 1

    runtime = _runtime_budget_quality(usage, budget)
    assert runtime["passed"] is True
    assert runtime["actual"]["web_fetches"] <= budget.web_fetch_limit
    assert runtime["actual"]["web_fetch_attempts"] <= budget.web_fetch_attempts
    assert runtime["actual"]["depth_queries"] <= budget.depth_query_limit

    overflow = {**usage, "web_fetches": budget.web_fetch_limit + 1}
    overflow_runtime = _runtime_budget_quality(overflow, budget)
    assert overflow_runtime["passed"] is False
    assert overflow_runtime["within_limits"]["web_fetches"] is False


def test_targeted_gap_plan_can_use_remaining_web_budget_after_zero_share() -> None:
    from conflux.graph_p15 import _targeted_gap_plans
    from conflux.research_protocol import SourcePlan

    budget = DynamicResearchBudget(
        depth_query_limit=2,
        web_fetch_limit=2,
        web_fetch_attempts=4,
        max_gap_iterations=1,
    )
    plan = SourcePlan(
        id="source-plan-gap",
        dimension_id="reliability",
        source_ids=["builtin.web", "builtin.model"],
        query_intents=["Original gap query"],
        budget={"queries": 1, "web_fetches": 0},
    )
    state = {
        "_source_plans": [plan.to_dict()],
        "_domain_map": {
            "dimensions": [
                {"id": "reliability", "name": "Reliability", "importance": 0.9}
            ]
        },
        "_coverage_matrix": {
            "dimensions": [
                {"dimension_id": "reliability", "status": "partial"}
            ]
        },
        "_budget_usage": {
            "web_fetches": 0,
            "gap_iterations": 0,
        },
    }

    targeted = _targeted_gap_plans(
        state,
        ["Find independent reliability evidence."],
        budget,
    )

    assert len(targeted) == 1
    assert targeted[0].budget["web_fetches"] == 1


def test_verifier_gap_loop_does_not_start_inside_ninety_second_reserve(monkeypatch) -> None:
    from conflux import graph_p15
    from conflux.research_modes import resolve_research_profile
    from conflux.research_protocol import SourcePlan

    profile = resolve_research_profile("standard")
    plan = SourcePlan(
        id="gap-plan",
        dimension_id="reliability",
        source_ids=["builtin.web"],
        query_intents=["Find independent evidence."],
        budget={"queries": 1, "web_fetches": 1, "web_fetch_attempts": 1},
    )
    monkeypatch.setattr(graph_p15, "_targeted_gap_plans", lambda *args: [plan])
    monkeypatch.setattr(
        graph_p15,
        "_budgeted_source_tasks",
        lambda *args, **kwargs: {"RAG": [], "Web": [{"query": "gap"}]},
    )
    state = {
        "_gap_questions": ["Find independent evidence."],
        "_research_budget": DynamicResearchBudget(
            depth_query_limit=2,
            web_fetch_limit=2,
            web_fetch_attempts=2,
            max_gap_iterations=1,
        ).to_dict(),
        "_budget_usage": {},
        "_source_statuses": {"Web": {"status": "success"}},
        "_deadline_at": time.time() + 89,
    }

    assert graph_p15._p15_verification_router(state, profile) == "finalize"
    state["_deadline_at"] = time.time() + 91
    assert graph_p15._p15_verification_router(state, profile) == "targeted_gap_research"


def test_p15_primary_retrieval_does_not_start_inside_commit_reserve() -> None:
    from conflux.graph_p15 import _source_plan_research_node
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import parse_source_results

    profile = resolve_research_profile("standard")
    state = {
        "_deadline_at": time.time() + profile.commit_reserve_seconds - 1,
        "_commit_reserve_seconds": profile.commit_reserve_seconds,
    }

    result = _source_plan_research_node(state, object(), "Web", profile)
    source_result = parse_source_results(result["web_result"])[-1]

    assert source_result.status == "fallback"
    assert "commit reserve" in source_result.error


SOURCE_ROUTES = {
    "rag_success_web_success": {"builtin.rag", "builtin.web", "builtin.model"},
    "rag_no_evidence_web_success": {"builtin.web", "builtin.model"},
    "rag_failed_web_success": {"builtin.web", "builtin.model"},
    "rag_success_web_failed": {"builtin.rag", "builtin.model"},
    "both_external_failed": {"builtin.model"},
    # Low relevance remains retryable for routing, but its snippet is not evidence.
    "web_snippet_without_body": {"builtin.web", "builtin.model"},
}


@pytest.mark.parametrize(
    "scenario",
    json.loads((FIXTURES / "source_scenarios.json").read_text(encoding="utf-8"))[
        "scenarios"
    ],
    ids=lambda scenario: scenario["id"],
)
def test_source_failure_matrix_routes_only_available_sources(scenario: dict[str, object]) -> None:
    domain_map = _domain_map(1, scope="current implementation status in 2026")

    plans = build_source_plans(
        domain_map,
        _comparison_archetype(),
        source_health=scenario["statuses"],
    )

    assert len(plans) == 1
    assert set(plans[0].source_ids) == SOURCE_ROUTES[str(scenario["id"])]
    assert plans[0].source_ids[-1] == "builtin.model"


def test_coverage_matrix_distinguishes_body_snippets_conflicts_and_scarcity() -> None:
    domain_map = DomainMap(
        scope="coverage behavior",
        dimensions=[
            ResearchDimension(id="covered", name="Covered", importance=0.7),
            ResearchDimension(id="snippet", name="Snippet only", importance=0.7),
            ResearchDimension(id="conflict", name="Conflicting", importance=0.9),
            ResearchDimension(id="scarce", name="Scarce", importance=0.8),
            ResearchDimension(
                id="excluded",
                name="Excluded",
                importance=0.2,
                current_coverage="out_of_scope",
            ),
        ],
    )
    evidence = [
        {
            "id": "e-covered",
            "dimension_id": "covered",
            "source": "Web",
            "url": "https://official.example/covered",
            "content_kind": "html_body",
            "verbatim_quote": "The body directly supports the claim.",
            "authority": 0.9,
        },
        {
            "id": "e-snippet",
            "dimension_id": "snippet",
            "source": "Web",
            "url": "https://search.example/snippet",
            "content_kind": "snippet",
            "verbatim_quote": "A search result snippet is discovery metadata only.",
            "authority": 0.9,
        },
        {
            "id": "e-conflict-a",
            "dimension_id": "conflict",
            "source": "RAG",
            "document_id": "paper-a",
            "content_kind": "full_text",
            "verbatim_quote": "The first source defines a broad audit scope.",
            "authority": 0.9,
            "conflict": "sources use different audit scope definitions",
        },
        {
            "id": "e-conflict-b",
            "dimension_id": "conflict",
            "source": "Web",
            "url": "https://official.example/audit",
            "content_kind": "html_body",
            "verbatim_quote": "The second source defines a narrow audit scope.",
            "authority": 0.9,
        },
    ]

    matrix = build_coverage_matrix(domain_map, evidence)
    rows = matrix.by_dimension()

    assert rows["covered"].status == "covered"
    assert rows["covered"].body_evidence is True
    assert rows["snippet"].status == "partial"
    assert rows["snippet"].body_evidence is False
    assert rows["conflict"].status == "conflicting"
    assert rows["conflict"].conflicts
    assert rows["scarce"].status == "evidence_scarce"
    assert rows["scarce"].evidence_count == 0
    assert rows["excluded"].status == "out_of_scope"


def test_gap_priority_prefers_important_conflicts_and_omits_completed_work() -> None:
    domain_map = DomainMap(
        dimensions=[
            ResearchDimension(id="done", name="Done", importance=1.0),
            ResearchDimension(id="conflict", name="Conflict", importance=0.95),
            ResearchDimension(id="partial", name="Partial", importance=0.6),
            ResearchDimension(id="excluded", name="Excluded", importance=1.0),
        ]
    )
    matrix = CoverageMatrix(
        dimensions=[
            CoverageDimension(dimension_id="done", status="covered", high_authority_source=True),
            CoverageDimension(
                dimension_id="conflict",
                status="conflicting",
                conflicts=["two definitions disagree"],
                cross_validation_required=True,
                independent_source_count=1,
            ),
            CoverageDimension(
                dimension_id="partial",
                status="partial",
                body_evidence=True,
                missing_actions=["identify_tradeoffs"],
            ),
            CoverageDimension(dimension_id="excluded", status="out_of_scope"),
        ]
    )

    gaps = prioritize_coverage_gaps(domain_map, matrix)

    assert [item["dimension_id"] for item in gaps] == ["conflict", "partial"]
    assert gaps[0]["priority"] > gaps[1]["priority"]


def test_research_stop_combines_coverage_saturation_and_budget() -> None:
    budget = DynamicResearchBudget(max_gap_iterations=2, timeout_seconds=100)

    complete = CoverageMatrix(
        dimensions=[CoverageDimension(dimension_id="a", status="covered")]
    )
    assert research_should_stop(complete, budget) == (True, "coverage_complete")

    saturated = CoverageMatrix(
        dimensions=[CoverageDimension(dimension_id="a", status="partial", evidence_count=3)],
        overall_coverage=0.85,
        high_importance_coverage=0.92,
        saturation=0.8,
    )
    assert research_should_stop(saturated, budget) == (
        True,
        "coverage_and_saturation_reached",
    )

    gaps_remain = CoverageMatrix(
        dimensions=[CoverageDimension(dimension_id="a", status="partial", evidence_count=1)],
        iteration=1,
        overall_coverage=0.4,
        high_importance_coverage=0.4,
        saturation=0.3,
    )
    assert research_should_stop(gaps_remain, budget, evidence_growth=0.4) == (
        False,
        "continue_for_coverage_gaps",
    )

    exhausted = CoverageMatrix(
        dimensions=[CoverageDimension(dimension_id="a", status="partial")],
        iteration=2,
    )
    assert research_should_stop(exhausted, budget) == (
        True,
        "gap_iteration_budget_exhausted",
    )

    quick_budget = DynamicResearchBudget(max_gap_iterations=0, timeout_seconds=100)
    initial_quick_matrix = CoverageMatrix(
        dimensions=[CoverageDimension(dimension_id="a", status="partial")],
        iteration=0,
    )
    assert research_should_stop(initial_quick_matrix, quick_budget) == (
        True,
        "gap_iteration_budget_exhausted",
    )
