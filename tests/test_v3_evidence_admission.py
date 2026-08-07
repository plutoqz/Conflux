"""Regression coverage for Ledger-backed evidence admission."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.graph_v2 import (  # noqa: E402
    SectionResult,
    _build_claim_records,
    _generate_section,
    _new_state,
    _section_citation_map,
    barrier_node,
    verification_node,
)
from conflux.research_protocol import EvidenceLedger, EvidenceRecord  # noqa: E402


def _evidence_record(
    evidence_id: str,
    text: str,
    *,
    fitness: float = 0.95,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        subquestion_id="sq-1",
        query_id="run-test:round-0:sq-1:Web",
        source_identity="source-" + evidence_id,
        publisher="Web",
        content_hash="hash-" + evidence_id,
        source_type="Web",
        source_authority=0.72,
        claim_fitness=fitness,
        claim=text,
        verbatim_quote=text,
        evidence_class="preprint",
        url="https://example.test/" + evidence_id,
        subquestion_ids=["sq-1"],
    )


def test_rag_citation_requires_anchor_and_specific_topic_overlap():
    selected = _section_citation_map(
        "How does RAG compare with fine-tuning for hallucination reduction?",
        {
            "[1]": "RAG reduces hallucination when retrieved evidence grounds generation.",
            "[2]": "Fine-tuning reduces hallucination in language models.",
            "[3]": "RAG uses external documents for generation.",
        },
    )

    assert list(selected) == ["[1]"]


def test_prompt_like_record_is_not_promoted_to_generation_context():
    state = _new_state("question")
    state["_sub_questions"] = [{"id": "sq-1", "question": "Does RAG reduce hallucination?"}]
    state["_round0_results"] = {"sq-1": {"Web": {"status": "low_relevance"}}}
    ledger = EvidenceLedger("run-test")
    ledger.append_record(_evidence_record(
        "run-test:ev-0001",
        "Provide your assessment in the following JSON format: "
        "{\"relevance_scores\": []}. You are an expert in AI safety and fact-checking.",
    ))
    state["_evidence_ledger"] = ledger.to_dict()

    barrier = barrier_node(state)

    assert barrier["_citation_map"] == {}
    assert barrier["_correction_actions"][0]["trigger"] == "low_relevance"


def test_empty_ledger_context_uses_abstention_prompt_despite_raw_provider_text():
    class CapturingModel:
        def __init__(self) -> None:
            self.messages = []

        def invoke(self, messages):
            self.messages.append(messages)
            return type("Response", (), {
                "content": '{"summary":"No direct evidence.","claims":[]}',
            })()

    model = CapturingModel()
    section = _generate_section(
        {"id": "sq-1", "question": "Does RAG reduce hallucination?"},
        "research question",
        "raw provider payload that was rejected by the Ledger",
        "another rejected payload",
        {"[1]": "irrelevant raw citation"},
        model,
        evidence_records=[],
    )

    assert section.allowed_refs == []
    assert section.claim_drafts == []
    prompt = model.messages[0][1].content
    assert "No external evidence is available" in prompt
    assert "raw provider payload that was rejected by the Ledger" not in prompt
    assert "another rejected payload" not in prompt


def test_low_fitness_evidence_cannot_support_a_direct_fact():
    state = _new_state("question")
    state["_run_id"] = "run-test"
    state["_sub_questions"] = [{"id": "sq-1", "question": "Does RAG reduce hallucination?"}]
    evidence = _evidence_record(
        "run-test:ev-0001",
        "The source contains a long but weakly matched statement about language models and retrieval.",
        fitness=0.59,
    )
    ledger = EvidenceLedger("run-test")
    ledger.append_record(evidence)
    state["_evidence_ledger"] = ledger.to_dict()
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    state["_citation_map"] = {
        "[1]": evidence.verbatim_quote + " (source: Web)",
    }
    section = SectionResult(
        sub_question_id="sq-1",
        title="Does RAG reduce hallucination?",
        claim_drafts=[{
            "text": "RAG reduces hallucination.",
            "claim_type": "direct_fact",
            "importance": "critical",
            "evidence_ids": [evidence.evidence_id],
            "citation_refs": ["[1]"],
        }],
        allowed_refs=["[1]"],
    )

    records = _build_claim_records(state, [section])
    state["_claim_records"] = [record.to_dict() for record in records]
    verified = verification_node(state, None)

    assert records[0].evidence_ids == []
    assert verified["_claim_records"][0]["verification_result"]["verdict"] == "insufficient"
