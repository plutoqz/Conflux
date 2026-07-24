from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from langchain_core.messages import HumanMessage

from conflux.model_factory import (
    BudgetedChatModel,
    MAX_ESTIMATED_INPUT_TOKENS,
    ResearchTokenBudget,
    _estimate_input_tokens,
    create_research_models,
)
from conflux.research_modes import resolve_research_profile


class _NoopModel:
    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, *args, **kwargs):
        raise AssertionError("not invoked")


class _FailingModel:
    def invoke(self, *args, **kwargs):
        raise ValueError("fixture failure")


class _UsageModel:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens

    def invoke(self, *args, **kwargs):
        from langchain_core.messages import AIMessage

        return AIMessage(
            content="ok",
            usage_metadata={
                "input_tokens": max(0, self.total_tokens - 1),
                "output_tokens": 1,
                "total_tokens": self.total_tokens,
            },
        )


def test_concurrent_token_reservations_cannot_overcommit() -> None:
    budget = ResearchTokenBudget(100)

    def reserve() -> bool:
        try:
            budget.reserve(60)
        except RuntimeError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))

    assert sorted(results) == [False, True]
    assert budget.reserved == 60
    assert budget.used == 0


def test_model_exception_releases_token_reservation() -> None:
    budget = ResearchTokenBudget(100)
    model = BudgetedChatModel(
        _FailingModel(),
        budget,
        output_reserve=10,
        role="fixture",
    )

    with pytest.raises(ValueError, match="fixture failure"):
        model.invoke([HumanMessage(content="short prompt")])

    assert budget.reserved == 0
    assert budget.used == 0


def test_downstream_reserve_blocks_early_call() -> None:
    budget = ResearchTokenBudget(100)
    model = BudgetedChatModel(
        _NoopModel(),
        budget,
        output_reserve=30,
        role="retrieval",
        downstream_reserve=70,
    )

    with pytest.raises(RuntimeError, match="preserved downstream"):
        model.invoke([HumanMessage(content="x")])

    assert budget.reserved == 0
    assert budget.used == 0


def test_actual_usage_cannot_consume_downstream_floor() -> None:
    budget = ResearchTokenBudget(100)
    model = BudgetedChatModel(
        _UsageModel(90),
        budget,
        output_reserve=10,
        role="analysis",
        downstream_reserve=40,
    )

    model.invoke([HumanMessage(content="small")])

    assert budget.actual_used == 90
    assert budget.used == 60
    assert budget.telemetry["preserve_clamps"] == 1
    assert budget.telemetry["roles"]["analysis"]["actual_tokens"] == 90


def test_stage_specific_clone_shares_budget_and_changes_floor() -> None:
    budget = ResearchTokenBudget(100)
    base = BudgetedChatModel(
        _UsageModel(30),
        budget,
        output_reserve=5,
        role="verifier",
    )
    early = base.with_downstream_reserve(50, role="evidence_verifier")

    early.invoke([HumanMessage(content="small")])

    assert budget.used == 30
    assert early._budget is base._budget
    assert early._downstream_reserve == 50


def test_stage_policy_changes_time_and_token_floor_without_splitting_budget() -> None:
    from conflux.model_factory import BoundedChatModel

    budget = ResearchTokenBudget(100)
    base = BudgetedChatModel(
        BoundedChatModel(_UsageModel(10), 20, commit_reserve_seconds=5, role="verifier"),
        budget,
        output_reserve=5,
        role="verifier",
    )

    stage = base.with_stage_policy(
        downstream_reserve=40,
        commit_reserve_seconds=30,
        max_output_tokens=3,
        role="evidence_verifier",
    )

    assert stage._budget is base._budget
    assert stage._downstream_reserve == 40
    assert stage._model._commit_reserve_seconds == 30
    assert stage._output_reserve == 3
    assert stage._role == "evidence_verifier"


def test_structured_input_estimate_is_capped() -> None:
    message = HumanMessage(content=[
        {"type": "text", "text": "x" * 200_000},
        {"type": "metadata", "payload": {"rows": ["y" * 10_000] * 20}},
    ])

    estimate = _estimate_input_tokens(([message],), {})

    assert estimate == MAX_ESTIMATED_INPUT_TOKENS


def test_p15_role_models_preserve_downstream_stage_windows(monkeypatch) -> None:
    monkeypatch.setattr("conflux.model_factory.create_chat_model", lambda *args, **kwargs: _NoopModel())
    profile = resolve_research_profile("standard")

    models, diagnostics = create_research_models(
        "standard",
        deadline_at=time.time() + profile.timeout_seconds,
        preserve_stage_budgets=True,
    )

    stage = profile.stage_budgets
    expected = {
        "planner": stage["retrieval"] + stage["analysis"] + stage["synthesis"] + stage["verification"] + stage["commit"],
        "reranker": stage["analysis"] + stage["synthesis"] + stage["verification"] + stage["commit"],
        "analyst": stage["synthesis"] + stage["verification"] + stage["commit"],
        "synthesizer": stage["verification"] + stage["commit"],
        "verifier": stage["commit"],
    }

    assert diagnostics["role_downstream_reserve_seconds"] == expected
    assert diagnostics["role_downstream_reserve_tokens"]["analyst"] >= 30_000
    assert diagnostics["role_downstream_reserve_tokens"]["synthesizer"] >= 12_000
    assert diagnostics["token_budget_runtime"]["limit_tokens"] == profile.token_budget
    assert models["planner"]._model._commit_reserve_seconds == expected["planner"]
    assert models["synthesizer"]._model._commit_reserve_seconds == expected["synthesizer"]
    assert expected["planner"] > expected["reranker"] > expected["analyst"] > expected["synthesizer"] > expected["verifier"]


def test_p15_planner_recovers_its_window_after_runtime_initialization(monkeypatch) -> None:
    monkeypatch.setattr("conflux.model_factory.create_chat_model", lambda *args, **kwargs: _NoopModel())
    profile = resolve_research_profile("standard")
    remaining_after_initialization = profile.timeout_seconds - 20

    models, diagnostics = create_research_models(
        "standard",
        deadline_at=time.time() + remaining_after_initialization,
        preserve_stage_budgets=True,
    )

    planner_reserve = models["planner"]._model._commit_reserve_seconds
    planner_window = remaining_after_initialization - planner_reserve
    assert planner_window >= profile.stage_budgets["planning"]
    assert diagnostics["planner_reserve_reclaimed_seconds"] >= 19
    assert models["reranker"]._model._commit_reserve_seconds == (
        profile.stage_budgets["analysis"]
        + profile.stage_budgets["synthesis"]
        + profile.stage_budgets["verification"]
        + profile.stage_budgets["commit"]
    )


def test_evidence_verifier_has_a_bounded_pre_synthesis_window() -> None:
    from conflux.graph_p15 import _evidence_verifier_commit_reserve

    profile = resolve_research_profile("standard")
    downstream = (
        profile.stage_budgets["synthesis"]
        + profile.stage_budgets["verification"]
        + profile.stage_budgets["commit"]
    )

    reserve = _evidence_verifier_commit_reserve(profile)

    assert 10 <= downstream - reserve <= 15
    assert reserve >= (
        profile.stage_budgets["verification"]
        + profile.stage_budgets["commit"]
    )


def test_conflict_arbitration_payload_is_bounded_and_keeps_referenced_evidence() -> None:
    from conflux.graph_p1 import _conflict_arbitration_payload

    evidence = [
        {
            "id": f"evidence-{index}",
            "source": "Web",
            "claim": f"Claim {index} " + "c" * 1200,
            "verbatim_quote": "q" * 2400,
            "evidence_refs": [f"https://example.test/{index}"],
            "evidence_class": "authoritative_document",
            "relevance": 0.9,
            "directness": 0.9,
        }
        for index in range(80)
    ]
    conflicts = [
        {
            "claim": f"Conflict {index} " + "x" * 1200,
            "evidence_ids": [f"evidence-{index * 2}", f"evidence-{index * 2 + 1}"],
            "reason": "different definitions " + "r" * 800,
        }
        for index in range(30)
    ]

    compact_conflicts, compact_evidence = _conflict_arbitration_payload(
        evidence,
        conflicts,
        query="foundation model transparency policy",
    )

    assert len(compact_conflicts) == 10
    assert len(compact_evidence) == 20
    assert {item["id"] for item in compact_evidence} == {
        f"evidence-{index}" for index in range(20)
    }
    assert all(len(item["verbatim_quote"]) <= 900 for item in compact_evidence)
    assert len(json.dumps([compact_conflicts, compact_evidence])) < 40_000
