"""B2/B3/B4 isolation and multi-subquestion replay checks."""

from __future__ import annotations

import json
from pathlib import Path

from conflux.graph_v2 import _new_state, create_v2_research_graph
from conflux.replay import ReplayModel, ReplayTool
from conflux.research_modes import resolve_research_profile


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "evaluation" / "v2_gold" / "replay" / "evidenceledger-limitations-baseline.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _run(variant: str) -> dict:
    bundle = _fixture()
    models = {
        role: ReplayModel.from_payload(payload, role=role)
        for role, payload in bundle["models"].items()
    }
    graph = create_v2_research_graph(
        ReplayTool.from_payload("RAG", bundle["retrieval"]["RAG"]),
        ReplayTool.from_payload("Web", bundle["retrieval"]["Web"]),
        planner_model=models["planner"],
        synthesizer_model=models["synthesizer"],
        independent_model=models["analyst"],
        arbitration_model=models["planner"],
        verifier_model=models["verifier"],
        profile=resolve_research_profile("deep"),
        run_id=bundle["run_id"],
        baseline_variant=variant,
        max_parallel_subquestions=1,
        rag_available=True,
        web_available=True,
    )
    return graph.invoke(_new_state(
        bundle["query"],
        run_id=bundle["run_id"],
        depth="deep",
        baseline_variant=variant,
    ))


def test_b2_b3_b4_change_only_the_intended_workflow_policy():
    b2 = _run("B2")
    b3 = _run("B3")
    b4 = _run("B4")

    assert b2["_baseline_policy"]["claim_verification_enabled"] is False
    assert b2["_model_verification"] == {}
    assert b2["_attribution_audit"] == {}
    assert b2["_budget_state"]["hard_limits"] == {}
    assert b2["_budget_state"]["model_calls"] == 8
    assert b2["_factcheck_status"] == "failed"
    assert {item["source"] for item in b2["_correction_actions"]} == {"RAG"}

    assert b3["_baseline_policy"]["claim_verification_enabled"] is True
    assert b3["_model_verification"]["status"] == "completed"
    assert b3["_attribution_audit"]["generation_trace_invalid"] is False
    assert b3["_budget_state"]["hard_limits"] == {}
    assert b3["_budget_state"]["model_calls"] == 9
    assert b3["_factcheck_status"] == "passed"

    assert b4["_baseline_policy"]["hard_budget_enforced"] is True
    assert b4["_budget_state"]["hard_limits"]["model_calls"] == 10
    assert b4["_budget_state"]["model_calls"] == 9
    assert b4["_factcheck_status"] == "passed"
    assert {item["source"] for item in b4["_correction_actions"]} == {"Web"}


def test_multi_subquestion_replay_is_deterministic_and_renders_empty_claims_as_text():
    first = _run("B4")
    second = _run("B4")

    assert first["_report_markdown"] == second["_report_markdown"]
    assert first["_ledger_snapshot"] == second["_ledger_snapshot"]
    assert first["_claim_records"] == second["_claim_records"]
    no_evidence_section = next(
        section for section in first["_section_results"] if section["sub_question_id"] == "sq-4"
    )
    assert no_evidence_section["body"] == "No direct evidence was returned for this requested limitation."
    assert not no_evidence_section["claim_drafts"]
