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
    _new_state,
    _subquestion_query,
    attribution_audit_node,
    arbitration_node,
    barrier_node,
    independent_analysis_node,
    retrieve_node,
    verification_node,
)
from conflux.research_protocol import EvidenceLedger, LedgerSnapshot  # noqa: E402
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
