from __future__ import annotations

from conflux.graph_p15 import _generalized_planning_node, _targeted_gap_plans
from conflux.research_generalization import (
    anchor_domain_map,
    build_domain_map,
    build_scope_contract,
    build_source_plans,
    classify_query_archetype,
)
from conflux.research_modes import resolve_research_profile
from conflux.research_protocol import DynamicResearchBudget, SourcePlan


QUERY = "GIS处理自动化研究目前有哪些瓶颈？"


def test_scope_contract_extracts_complete_chinese_subject_and_entity() -> None:
    archetype = classify_query_archetype(QUERY, user_intent=QUERY)
    scope = build_scope_contract(QUERY, archetype)

    assert scope.subject == "GIS处理自动化研究"
    assert scope.required_entities == ["GIS"]
    assert scope.original_query == QUERY

    shortened = build_scope_contract(
        QUERY,
        archetype,
        planner_payload={"subject": "GIS"},
    )
    assert shortened.subject == "GIS处理自动化研究"


def test_all_source_plan_queries_retain_scope_subject() -> None:
    archetype = classify_query_archetype(QUERY, user_intent=QUERY)
    scope = build_scope_contract(QUERY, archetype)
    domain_map = anchor_domain_map(build_domain_map(QUERY, archetype), scope)

    plans = build_source_plans(domain_map, archetype, scope_contract=scope)

    assert plans
    assert all(
        scope.subject in question
        for plan in plans
        for question in plan.query_intents
    )


def test_planner_timeout_falls_back_once_and_stays_domain_anchored() -> None:
    class TimeoutPlanner:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, messages):
            self.calls += 1
            raise TimeoutError("fixture timeout")

    planner = TimeoutPlanner()
    state = {
        "query": QUERY,
        "_run_summary": {"started_at": 0.0, "stages": []},
        "_source_statuses": {},
    }

    result = _generalized_planning_node(
        state,
        planner,
        resolve_research_profile("standard"),
    )

    assert planner.calls == 1
    assert result["_scope_contract"]["subject"] == "GIS处理自动化研究"
    assert all(
        "GIS处理自动化研究" in question
        for plan in result["_source_plans"]
        for question in plan["query_intents"]
    )


def test_planner_prompt_omits_redundant_strategy_and_claim_payloads() -> None:
    from langchain_core.messages import AIMessage

    class CapturingPlanner:
        prompt = ""

        def invoke(self, messages):
            self.prompt = str(messages[-1].content)
            return AIMessage(content="{}")

    planner = CapturingPlanner()
    _generalized_planning_node(
        {
            "query": QUERY,
            "_run_summary": {"started_at": 0.0, "stages": []},
            "_source_statuses": {},
        },
        planner,
        resolve_research_profile("standard"),
    )

    assert '"claims":' not in planner.prompt
    assert '"research_strategy":' not in planner.prompt
    assert "Keep the complete JSON under 6000 characters" in planner.prompt


def test_planner_fallback_builds_object_level_jurisdiction_map() -> None:
    class TimeoutPlanner:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, messages):
            self.calls += 1
            raise TimeoutError("fixture timeout")

    planner = TimeoutPlanner()
    result = _generalized_planning_node(
        {
            "query": "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？",
            "_run_summary": {"started_at": 0.0, "stages": []},
            "_source_statuses": {},
        },
        planner,
        resolve_research_profile("standard"),
    )

    dimensions = result["_domain_map"]["dimensions"]
    assert len(dimensions) == 5
    assert {item["id"] for item in dimensions} == {
        "jurisdiction-eu",
        "jurisdiction-us",
        "jurisdiction-uk",
        "jurisdiction-cn",
        "jurisdiction-cross-comparison",
    }
    assert all(item["required_actions"] for item in dimensions)
    assert planner.calls == 0
    assert all(
        plan["source_ids"] == ["builtin.web", "builtin.model"]
        for plan in result["_source_plans"]
    )
    assert result["_research_budget"]["major_dimension_limit"] >= 5


def test_targeted_gap_queries_are_reanchored() -> None:
    budget = DynamicResearchBudget(
        depth="standard",
        major_dimension_limit=2,
        breadth_query_limit=2,
        depth_query_limit=2,
        evidence_limit=4,
        web_fetch_limit=1,
        web_fetch_attempts=1,
        max_gap_iterations=1,
        total_output_chars=2000,
        timeout_seconds=240,
    )
    plan = SourcePlan(
        id="source-plan-1",
        dimension_id="limits",
        source_ids=["builtin.rag"],
        query_intents=["GIS处理自动化研究：已有瓶颈证据"],
        evidence_needs=["body"],
    )
    state = {
        "query": QUERY,
        "_scope_contract": {"subject": "GIS处理自动化研究"},
        "_research_budget": budget.to_dict(),
        "_source_plans": [plan.to_dict()],
        "_budget_usage": {},
    }

    targeted = _targeted_gap_plans(state, ["需要哪些失败模式证据？"], budget)

    assert targeted
    assert targeted[0].query_intents == ["GIS处理自动化研究：需要哪些失败模式证据？"]
