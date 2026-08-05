"""Budget, replay, and adversarial-flow checks for the V2 pipeline."""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

from conflux.graph_v2 import (
    _new_state,
    arbitration_node,
    create_v2_research_graph,
    independent_analysis_node,
    retrieve_node,
)
from conflux.replay import ReplayModel, ReplayTool
from conflux.research_modes import resolve_research_profile
from conflux.source_status import SourceResult


class _NoopModel:
    def __init__(self, content: str = "{}") -> None:
        self.content = content
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return type("Response", (), {"content": self.content})()


class _Tool:
    def __init__(self, source: str) -> None:
        self.source = source
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        return SourceResult(
            source=self.source,
            status="success",
            content="evidence",
            claims=[],
        ).to_tool_text()


def test_quick_budget_rejects_excess_round0_requests():
    state = _new_state("question", depth="quick")
    state["_sub_questions"] = [
        {"id": f"sq-{index}", "question": f"subquestion {index}", "search_queries": [f"q-{index}"]}
        for index in range(5)
    ]

    result = retrieve_node(
        state,
        _Tool("RAG"),
        _Tool("Web"),
    )

    budget = result["_budget_state"]
    assert budget["retrieval_requests"] == 8
    assert budget["dropped_reasons"]
    assert any("retrieval_dropped:round0" in reason for reason in budget["dropped_reasons"])


def test_model_budget_rejection_is_recorded_and_does_not_call_provider():
    state = _new_state("question", depth="quick")
    model = _NoopModel('{"summary":"ok"}')
    for _ in range(5):
        result = independent_analysis_node(state, model)
        state = {**state, **result}

    budget = state["_budget_state"]
    assert budget["model_calls"] == 4
    assert model.calls == 4
    assert any("model_call_dropped:independent_analysis" in reason for reason in budget["dropped_reasons"])


def _replay_bundle():
    run_id = "replay-run"
    evidence_id = f"{run_id}:ev-0001"
    claim_id = f"{run_id}:claim:sq-1:01"
    return {
        "schema_version": "conflux-v2-replay-v1",
        "run_id": run_id,
        "query": "How does replay verification work?",
        "depth": "standard",
        "prompt_version": "research-prompts-v3",
        "model_config_version": "research-model-profile-v1",
        "models": {
            "planner": {
                "responses": [
                    {
                        "content": '{"core_question":"How does replay verification work?","sub_questions":[{"question":"replay verification","search_queries":["replay verification"],"search_queries_en":[]}]}'
                    },
                    {
                        "content": '{"judgments":[{"subquestion_id":"sq-1","verdict":"covered","confidence":1.0}],"action_proposals":[]}'
                    },
                ]
            },
            "analyst": {"responses": [{"content": '{"summary":"independent replay analysis"}'}]},
            "synthesizer": {
                "responses": [
                    {
                        "content": (
                            '{"claims":[{"text":"Replay uses fixed provider responses.",'
                            '"claim_type":"direct_fact","importance":"high",'
                            f'"evidence_ids":["{evidence_id}"],"derivation_type":"direct_evidence",'
                            f'"citation_refs":["[1]"]}}]}}'
                        )
                    },
                    {
                        "content": (
                            '{"direct_claim_ids":['
                            f'"{claim_id}"],"cross_synthesis_claim_ids":["{claim_id}"]}}'
                        )
                    },
                ]
            },
            "verifier": {
                "responses": [
                    {
                        "content": (
                            '{"checks":[{"claim_id":"'
                            + claim_id
                            + '","verdict":"supports","confidence":1.0,'
                            f'"evidence_ids":["{evidence_id}"]}}}}'
                        )
                    }
                ]
            },
        },
        "retrieval": {
            "RAG": {
                "by_query": {
                    "replay verification": {
                        "status": "success",
                        "content": "Replay uses fixed provider responses.",
                        "claims": [{
                            "claim": "Replay uses fixed provider responses.",
                            "verbatim_quote": "Replay uses fixed provider responses.",
                            "source_identity": "replay-rag",
                            "content_hash": "replay-rag-hash",
                            "evidence_class": "authoritative_document",
                        }],
                    }
                }
            },
            "Web": {
                "by_query": {
                    "replay verification": {
                        "status": "no_evidence",
                        "content": "",
                    }
                }
            },
        },
    }


def _run_replay(bundle):
    models = {
        role: ReplayModel.from_payload(payload, role=role)
        for role, payload in bundle["models"].items()
    }
    rag = ReplayTool.from_payload("RAG", bundle["retrieval"]["RAG"])
    web = ReplayTool.from_payload("Web", bundle["retrieval"]["Web"])
    profile = resolve_research_profile("standard")
    graph = create_v2_research_graph(
        rag,
        web,
        planner_model=models["planner"],
        synthesizer_model=models["synthesizer"],
        independent_model=models["analyst"],
        arbitration_model=models["planner"],
        verifier_model=models["verifier"],
        profile=profile,
        run_id=bundle["run_id"],
        deadline_at=time.time() + 180,
        rag_available=True,
        web_available=True,
    )
    return graph.invoke(_new_state(bundle["query"], run_id=bundle["run_id"], depth="standard"))


def test_fixed_replay_runs_the_real_v2_graph_deterministically():
    bundle = _replay_bundle()
    first = _run_replay(bundle)
    second = _run_replay(copy.deepcopy(bundle))

    assert first["_report_markdown"] == second["_report_markdown"]
    assert first["_ledger_snapshot"] == second["_ledger_snapshot"]
    assert first["_claim_records"] == second["_claim_records"]
    assert first["_budget_state"]["model_calls"] == 6
    assert first["_budget_state"]["retrieval_requests"] == 2


def test_fixed_replay_cli_writes_report_trace_and_summary(tmp_path):
    from conflux.__main__ import query_command

    bundle_path = tmp_path / "replay.json"
    bundle_path.write_text(json.dumps(_replay_bundle(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "reports"

    query_command(
        _replay_bundle()["query"],
        output_dir=str(output_dir),
        trace_dir=str(output_dir),
        replay=str(bundle_path),
        depth="standard",
    )

    summary_path = output_dir / "replay-run.summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["replay_mode"] is True
    assert summary["budget_consumed"]["model_calls"] == 6
    assert Path(summary["report_md_path"]).exists()
    assert Path(summary["trace_path"]).exists()
    evidence = json.loads(Path(summary["report_evidence_path"]).read_text(encoding="utf-8"))
    assert evidence["budget_consumed"]["model_calls"] == 6
    trace_events = [
        json.loads(line)
        for line in Path(summary["trace_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    run_event = next(item for item in trace_events if item["stage"] == "v2_run_summary")
    assert run_event["metadata"]["budget_consumed"]["model_calls"] == 6
    assert "query_plan" in run_event["metadata"]
    assert "verification_result" in run_event["metadata"]


def test_research_positional_query_is_forwarded_without_dest_collision(monkeypatch):
    import conflux.__main__ as cli

    captured = {}
    monkeypatch.setattr(
        cli,
        "query_command",
        lambda query, **kwargs: captured.update(query=query, kwargs=kwargs),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["conflux", "research", "positional research question", "--depth", "quick"],
    )

    cli.main()

    assert captured["query"] == "positional research question"
    assert captured["kwargs"]["depth"] == "quick"
