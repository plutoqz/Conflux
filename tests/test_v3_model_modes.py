"""Regression tests for isolated Model modes in the V3 protocol."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.graph_v2 import (  # noqa: E402
    SectionResult,
    _build_claim_records,
    _generate_section,
    _new_state,
    _subquestion_query,
    attribution_audit_node,
    arbitration_node,
    barrier_node,
    independent_analysis_node,
    retrieve_node,
    verification_node,
)
from conflux.research_protocol import EvidenceLedger, EvidenceRecord, LedgerSnapshot  # noqa: E402
from conflux.source_status import EvidenceItem, SourceResult  # noqa: E402


class _Model:
    def __init__(self, payload: dict):
        self.payload = payload
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        return type("Response", (), {"content": json.dumps(self.payload)})()


class _Tool:
    def __init__(self, source: str):
        self.source = source

    def invoke(self, payload: dict) -> str:
        claim = EvidenceItem(
            claim="This source contains directly relevant evidence for the subquestion and its stated limitation.",
            source=self.source,
            verbatim_quote="This source contains directly relevant evidence for the subquestion and its stated limitation.",
            evidence_class="authoritative_document",
            source_identity=f"{self.source}-source",
            content_hash=f"{self.source}-hash",
        )
        return SourceResult(
            source=self.source,
            status="success",
            content=claim.claim,
            claims=[claim],
            evidence_class="authoritative_document",
        ).to_tool_text()


def test_round0_records_independent_analysis_after_retrieval():
    state = _new_state("original research question")
    state["_sub_questions"] = [
        {"id": "sq-1", "question": "subquestion", "search_queries": ["query"]},
    ]
    model = _Model({"summary": "model hypothesis", "hypotheses": ["h1"]})

    result = retrieve_node(
        state,
        _Tool("RAG"),
        _Tool("Web"),
        independent_model=model,
    )

    assert result["_independent_analysis"]["summary"] == "model hypothesis"
    judgments = result["_evidence_ledger"]["judgments"]
    assert judgments[0]["mode"] == "independent_analysis"
    assert "Immutable Ledger snapshot" not in model.messages[0][1].content


def test_model_modes_keep_system_prompts_and_context_isolated():
    state = _new_state("original question")
    state["_sub_questions"] = [
        {"id": "sq-1", "question": "subquestion", "importance": "high"},
    ]
    state["_independent_analysis"] = {"private_analysis_marker": "independent-only"}

    independent_model = _Model({"summary": "independent"})
    independent_analysis_node(state, independent_model)

    barrier = barrier_node(state)
    state = {**state, **barrier}
    state["_model_arbitration"] = {"private_arbitration_marker": "arbitration-only"}
    arbitration_model = _Model({
        "judgments": [{"subquestion_id": "sq-1", "verdict": "covered"}],
        "action_proposals": [],
    })
    arbitration_node(state, arbitration_model)

    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    state["_section_results"] = [{
        "sub_question_id": "sq-1",
        "title": "subquestion",
        "key_claims": ["atomic claim"],
    }]
    verification_model = _Model({
        "checks": [{
            "claim": "atomic claim",
            "verdict": "insufficient",
            "evidence_ids": [],
        }],
    })
    verification_node(state, verification_model)

    independent_system, independent_prompt = independent_model.messages[0]
    arbitration_system, arbitration_prompt = arbitration_model.messages[0]
    verification_system, verification_prompt = verification_model.messages[0]

    assert "independent research analyst" in independent_system.content
    assert "original question" in independent_prompt.content
    assert "independent-only" not in arbitration_prompt.content

    assert "evidence arbitration analyst" in arbitration_system.content
    assert "Immutable Ledger snapshot" in arbitration_prompt.content
    assert "arbitration-only" not in verification_prompt.content

    assert "independent evidence verifier" in verification_system.content
    assert "atomic claim" in verification_prompt.content
    assert "private_analysis_marker" not in verification_prompt.content


def test_claim_record_attribution_audit_rejects_unbound_body_citation():
    state = _new_state("question")
    state["_citation_map"] = {"[1]": "evidence one", "[2]": "evidence two"}
    section = SectionResult(
        sub_question_id="sq-1",
        title="section",
        body="正文引用了 [2]。",
        key_claims=["Claim supported by [1]"],
        citation_refs=["[2]"],
        allowed_refs=["[1]"],
    )
    state["_section_results"] = [section.to_dict()]
    state["_claim_records"] = [
        record.to_dict()
        for record in _build_claim_records(state, [section])
    ]

    result = attribution_audit_node(state)

    assert result["_generation_trace_invalid"] is True
    assert result["_attribution_audit"]["invalid_refs"]
    assert result["_attribution_audit"]["unattributed_refs"]


def test_verification_writes_verdict_to_claim_record():
    state = _new_state("question")
    state["_claim_records"] = [{
        "claim_id": "run-test:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "atomic claim",
        "derivation_inputs": ["[1]"],
        "generation_attribution": {"citation_refs": ["[1]"], "allowed_refs": ["[1]"]},
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    model = _Model({
        "checks": [{
            "claim_id": "run-test:claim:sq-1:01",
            "claim": "atomic claim",
            "verdict": "supports",
            "evidence_ids": [],
        }],
    })

    result = verification_node(state, model)

    assert result["_claim_records"][0]["verification_result"]["verdict"] == "supports"


def test_cross_language_queries_keep_source_specific_query_order():
    subquestion = {
        "question": "中文研究问题",
        "search_queries": ["中文检索词"],
        "search_queries_en": ["English retrieval query"],
    }

    assert _subquestion_query(subquestion, "RAG") == "中文检索词"
    assert _subquestion_query(subquestion, "Web") == "English retrieval query"


def test_arbitration_discards_untrusted_action_proposals():
    state = _new_state("question")
    state["_sub_questions"] = [{"id": "sq-1", "question": "subquestion"}]
    barrier = barrier_node(state)
    model = _Model({
        "action_proposals": [
            {"subquestion_id": "unknown", "source": "Web", "trigger": "no_evidence", "query": "bad"},
            {"subquestion_id": "sq-1", "source": "Shell", "trigger": "no_evidence", "query": "bad"},
            {"subquestion_id": "sq-1", "source": "RAG", "trigger": "no_evidence", "query": "bounded query"},
        ],
    })

    result = arbitration_node({**state, **barrier}, model)

    assert any(item["query"] == "bounded query" for item in result["_correction_actions"])
    assert all(item["subquestion_id"] == "sq-1" for item in result["_correction_actions"])
    assert all(item["source"] in {"RAG", "Web"} for item in result["_correction_actions"])


def test_model_mode_respects_deadline_budget():
    state = _new_state("question", deadline_at=time.time() - 1)
    model = _Model({"summary": "should not run"})

    result = independent_analysis_node(state, model)

    assert result["_independent_analysis"] == {}
    assert model.messages == []


def test_ledger_snapshot_round_trip_is_replayable():
    ledger = EvidenceLedger("replay-run")
    snapshot = ledger.freeze("round_0")
    replayed = LedgerSnapshot.from_dict(snapshot.to_dict())

    assert replayed.to_dict() == snapshot.to_dict()
    assert replayed.snapshot_id == "replay-run:snapshot-1"


def test_structured_claim_generation_populates_claim_record_protocol():
    state = _new_state("research question")
    evidence = EvidenceRecord(
        evidence_id="run-test:ev-0001",
        subquestion_id="sq-1",
        query_id="run-test:query-1",
        source_identity="source-a",
        publisher="Publisher",
        content_hash="hash-a",
        source_type="Web",
        evidence_class="authoritative_document",
        claim_fitness=0.95,
        claim="The source directly supports the atomic statement with enough context for verification.",
        verbatim_quote="The source directly supports the atomic statement with enough context for verification.",
    )
    ledger = EvidenceLedger("run-test")
    ledger.append_record(evidence)
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    state["_citation_map"] = {"[1]": "The source directly supports the atomic statement with enough context for verification.（来源：Web）"}

    model = _Model({
        "claims": [{
            "text": "The atomic statement is supported.",
            "claim_type": "direct_fact",
            "importance": "high",
            "evidence_ids": ["run-test:ev-0001"],
            "derivation_type": "direct_evidence",
            "derivation_inputs": [],
            "citation_refs": ["[1]"],
        }],
    })
    section = _generate_section(
        {"id": "sq-1", "question": "atomic statement"},
        "research question",
        "retrieved evidence",
        "retrieved evidence",
        state["_citation_map"],
        model,
        evidence_records=[{
            "evidence_id": "run-test:ev-0001",
            "citation_ref": "[1]",
            "claim": evidence.claim,
        }],
    )
    records = _build_claim_records(state, [section])

    assert records[0].claim_type == "direct_fact"
    assert records[0].importance == "high"
    assert records[0].evidence_ids == ["run-test:ev-0001"]
    assert records[0].generation_attribution["generation_trace"] == "structured_claims"


def test_verification_rejects_unsupported_direct_fact_even_when_model_says_supports():
    state = _new_state("question")
    state["_claim_records"] = [{
        "claim_id": "run-test:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "unsupported fact",
        "claim_type": "direct_fact",
        "importance": "critical",
        "evidence_ids": [],
        "derivation_type": "direct_evidence",
        "derivation_inputs": [],
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    result = verification_node(state, _Model({
        "checks": [{
            "claim_id": "run-test:claim:sq-1:01",
            "verdict": "supports",
            "confidence": 1.0,
            "evidence_ids": [],
        }],
    }))

    verification = result["_claim_records"][0]["verification_result"]
    assert verification["verdict"] == "insufficient"
    assert verification["verifier_version"] == "rules-v1"


def test_critical_claim_failure_blocks_claim_delivery():
    from conflux.graph_v2 import _claim_delivery_assessment

    state = _new_state("question")
    state["_claim_records"] = [{
        "claim_id": "run-test:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "critical fact",
        "claim_type": "direct_fact",
        "importance": "critical",
        "evidence_ids": [],
        "derivation_type": "direct_evidence",
        "verification_result": {
            "verdict": "insufficient",
            "confidence": 0.0,
            "reason": "no support",
            "verifier_version": "rules-v1",
        },
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()

    assessment = _claim_delivery_assessment(state)

    assert assessment["status"] == "diagnostic_only"
    assert "critical_claim_not_supported" in assessment["hard_failures"]


def test_analysis_only_claims_are_limited_instead_of_diagnostic():
    from conflux.graph_v2 import _claim_delivery_assessment

    state = _new_state("question")
    state["_claim_records"] = [{
        "claim_id": "run-test:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "bounded analysis",
        "claim_type": "model_analysis",
        "importance": "high",
        "evidence_ids": [],
        "derivation_type": "model_analysis",
        "verification_result": {
            "verdict": "supports",
            "confidence": 1.0,
            "reason": "explicitly marked as model analysis",
            "verifier_version": "rules-v1",
        },
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()

    assessment = _claim_delivery_assessment(state)

    assert assessment["status"] == "limited"
    assert assessment["hard_failures"] == []
    assert assessment["limitations"] == ["analysis_only_claims"]

# --- P2.1：逐阶段预算可观测性（每次调用记录 §7.5 字段 + 对账） ---


def _budget_fake_model(*, usage=None, finish_reason="stop", raise_exc=None):
    from types import SimpleNamespace

    class FakeModel:
        def invoke(self, messages):
            if raise_exc is not None:
                raise raise_exc
            response_metadata = {"finish_reason": finish_reason}
            return SimpleNamespace(
                usage_metadata=usage or {}, response_metadata=response_metadata, content="ok"
            )

    return FakeModel()


def test_budget_records_per_call_ledger_fields():
    from conflux.model_factory import (
        BudgetedChatModel,
        ResearchTokenBudget,
        research_call_stage,
    )

    budget = ResearchTokenBudget(75_000)
    model = BudgetedChatModel(
        _budget_fake_model(
            usage={"input_tokens": 120, "output_tokens": 45, "total_tokens": 165}
        ),
        budget,
        output_reserve=4096,
        role="planner",
        downstream_reserve=2000,
        preset="standard",
    )
    from types import SimpleNamespace

    with research_call_stage("decompose"):
        model.invoke([SimpleNamespace(content="plan [RAG:src-1] [WEB:src-2]")])

    call = budget.telemetry["calls"][0]
    for field in (
        "stage", "role", "provider", "model", "revision_evidence", "prompt_hash",
        "input_tokens", "output_tokens", "reserved_tokens", "context_bytes",
        "evidence_refs_count", "latency_ms", "finish_reason", "estimated_cost",
    ):
        assert field in call, f"缺字段 {field}"
    assert call["stage"] == "decompose"
    assert call["role"] == "planner"
    assert call["revision_evidence"] == "unverified"
    assert call["prompt_hash"]
    assert call["input_tokens"] == 120
    assert call["output_tokens"] == 45
    assert call["total_tokens"] == 165
    assert call["reserved_tokens"] == 4096 + call["estimated_input_tokens"] + 2000
    assert call["context_bytes"] > 0
    assert call["evidence_refs_count"] == 2
    assert call["finish_reason"] == "stop"
    assert call["estimated_cost"] == "unknown"
    assert call["status"] == "ok"


def test_missing_provider_usage_records_unknown_not_estimates():
    from conflux.model_factory import BudgetedChatModel, ResearchTokenBudget

    budget = ResearchTokenBudget(75_000)
    model = BudgetedChatModel(
        _budget_fake_model(usage=None),
        budget,
        output_reserve=100,
        role="analyst",
        preset="standard",
    )
    from types import SimpleNamespace

    model.invoke([SimpleNamespace(content="some input text")])

    call = budget.telemetry["calls"][0]
    assert call["input_tokens"] == "unknown"
    assert call["output_tokens"] == "unknown"
    assert call["total_tokens"] == "unknown"
    assert isinstance(call["estimated_input_tokens"], int) and call["estimated_input_tokens"] > 0
    assert budget.reconciliation()["unknown_usage_calls"] == 1
    assert "unknown" in budget.reconciliation()["difference_explanation"]


def test_failed_call_records_failure_ledger_entry():
    from conflux.model_factory import BudgetedChatModel, ResearchTokenBudget

    budget = ResearchTokenBudget(75_000)
    model = BudgetedChatModel(
        _budget_fake_model(raise_exc=RuntimeError("provider down")),
        budget,
        output_reserve=100,
        role="verifier",
        preset="standard",
    )
    from types import SimpleNamespace

    try:
        model.invoke([SimpleNamespace(content="check")])
    except RuntimeError:
        pass
    else:
        raise AssertionError("invoke 应抛错")

    call = budget.telemetry["calls"][0]
    assert call["status"] == "failed"
    assert call["role"] == "verifier"
    assert call["input_tokens"] == "unknown"
    assert call["charged_tokens"] == 0
    assert budget.telemetry["failed_calls"] == 1


def test_reconciliation_explains_charge_differences():
    from conflux.model_factory import BudgetedChatModel, ResearchTokenBudget
    from types import SimpleNamespace

    budget = ResearchTokenBudget(500)
    model = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 200, "output_tokens": 200, "total_tokens": 400}),
        budget,
        output_reserve=150,
        role="synthesizer",
        downstream_reserve=250,
        preset="standard",
    )
    model.invoke([SimpleNamespace(content="synthesize")])

    recon = budget.reconciliation()
    assert budget.telemetry["preserve_clamps"] >= 1
    assert budget.telemetry["charged_tokens"] == 250  # 被下游 preserve 截断
    assert recon["sum_call_charged_tokens"] == recon["budget_accounting"]["charged_tokens"]
    assert "截断" in recon["difference_explanation"] or "preserve_clamps" in recon[
        "difference_explanation"
    ]
    assert recon["unallocated_tokens"] >= 0


def test_finalize_token_budget_runtime_adds_reconciliation():
    from conflux.model_factory import (
        BudgetedChatModel,
        ResearchTokenBudget,
        finalize_token_budget_runtime,
    )
    from types import SimpleNamespace

    budget = ResearchTokenBudget(75_000)
    model = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}),
        budget,
        output_reserve=100,
        role="planner",
        preset="standard",
    )
    model.invoke([SimpleNamespace(content="hello")])

    telemetry = finalize_token_budget_runtime(dict(budget.telemetry))
    assert "reconciliation" in telemetry
    assert telemetry["reconciliation"]["sum_call_total_tokens"] == 15
    assert len(telemetry["calls"]) == 1


def test_scoped_node_records_stage_for_nested_model_calls():
    from conflux.graph_v2 import _scoped_node
    from conflux.model_factory import BudgetedChatModel, ResearchTokenBudget
    from types import SimpleNamespace

    budget = ResearchTokenBudget(75_000)
    model = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}),
        budget,
        output_reserve=10,
        role="synthesizer",
        preset="standard",
    )

    def generate(state, wrapped):
        wrapped.invoke([SimpleNamespace(content="draft section")])
        return {"_pipeline_stage": "generated"}

    scoped = _scoped_node("generate", generate, model)
    scoped({"query": "q"})

    assert budget.telemetry["calls"][0]["stage"] == "generate"

# --- P2.2：交付预算硬保留（数据驱动 P90+余量，不写死百分比） ---


def test_percentile_nearest_rank():
    from conflux.model_factory import percentile

    assert percentile([], 0.9) == 0
    assert percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 0.9) == 90
    assert percentile([5], 0.9) == 5


def test_stage_reserves_from_ledger_p90_plus_margin_and_unknown_accounting():
    from conflux.model_factory import stage_reserves_from_ledger

    calls = [
        {"status": "ok", "stage": "synthesize", "total_tokens": 100 + i * 100}
        for i in range(10)
    ]
    calls.append({"status": "ok", "stage": "synthesize", "total_tokens": "unknown"})
    calls.append({"status": "ok", "stage": "factcheck", "total_tokens": 500})
    calls.append({"status": "failed", "stage": "factcheck", "total_tokens": "unknown"})

    reserves = stage_reserves_from_ledger(calls, margin_ratio=0.2)
    synth = reserves["synthesize"]
    assert synth["samples"] == 10
    assert synth["unknown_usage_samples"] == 1
    assert synth["p90"] == 900
    assert synth["reserve"] == round(900 * 1.2)
    assert synth["basis"] == "observed_p90_plus_margin"
    assert reserves["factcheck"]["reserve"] == round(500 * 1.2)
    assert reserves["finalize"]["reserve"] == 0
    assert reserves["finalize"]["basis"] == "unmeasured_no_reserve"


def test_stage_preserve_protects_delivery_stages():
    from conflux.model_factory import (
        BudgetedChatModel,
        ResearchTokenBudget,
        research_call_stage,
    )
    from types import SimpleNamespace

    budget = ResearchTokenBudget(2000)
    stage_reserves = {"synthesize": 400, "factcheck": 300, "finalize": 200}
    model = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 50, "output_tokens": 50, "total_tokens": 100}),
        budget,
        output_reserve=100,
        role="analyst",
        preset="standard",
        stage_reserves=stage_reserves,
    )
    # generate 阶段：下游保护 = synthesize + factcheck + finalize = 900（104+900 <= 2000 可执行）
    with research_call_stage("generate"):
        model.invoke([SimpleNamespace(content="draft")])
    call = budget.telemetry["calls"][0]
    assert call["preserve_tokens"] == 900
    assert call["charged_tokens"] == 100

    # 保护底线：剩余可用 < 保护量时，前置阶段调用必须被拒绝而不是吃掉保底。
    budget2 = ResearchTokenBudget(1000)
    model2 = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 100, "output_tokens": 100, "total_tokens": 200}),
        budget2,
        output_reserve=100,
        role="reranker",
        preset="standard",
        stage_reserves=stage_reserves,
    )
    with research_call_stage("retrieve"):
        # required(100+~7) + preserve(900) > 1000 → 拒绝
        try:
            model2.invoke([SimpleNamespace(content="fetch evidence")])
        except RuntimeError as exc:
            assert "budget exhausted" in str(exc)
        else:
            raise AssertionError("前置阶段调用不应突破交付保底")
    assert budget2.telemetry["charged_tokens"] == 0
    assert budget2.telemetry["rejected_calls"] == 1


def test_stage_reserves_disabled_keeps_legacy_preserve():
    from conflux.model_factory import (
        BudgetedChatModel,
        ResearchTokenBudget,
        research_call_stage,
    )
    from types import SimpleNamespace

    budget = ResearchTokenBudget(10_000)
    model = BudgetedChatModel(
        _budget_fake_model(usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}),
        budget,
        output_reserve=50,
        role="planner",
        preset="standard",
        downstream_reserve=777,
    )
    with research_call_stage("decompose"):
        model.invoke([SimpleNamespace(content="plan")])
    assert budget.telemetry["calls"][0]["preserve_tokens"] == 777


def test_resolve_stage_token_reserves_from_config(monkeypatch):
    from conflux import config as config_module
    from conflux.model_factory import resolve_stage_token_reserves

    def fake_get(section, key, default=None):
        if section == "research" and key == "stage_token_reserves":
            return {"synthesize": "12000", "factcheck": "8000", "finalize": 0, "audit": "nope"}
        return default

    monkeypatch.setattr(config_module, "get", fake_get)
    assert resolve_stage_token_reserves() == {"synthesize": 12000, "factcheck": 8000}


