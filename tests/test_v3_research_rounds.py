"""回归测试：EvidenceLedger、按子问题检索和一次纠偏轮。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from conflux.graph_v2 import (  # noqa: E402
    _new_state,
    barrier_node,
    correction_node,
    retrieve_node,
)
from conflux.research_protocol import EvidenceLedger  # noqa: E402
from conflux.source_status import EvidenceItem, SourceResult  # noqa: E402


LONG_CLAIM = (
    "This source documents the directly relevant method, its observed result, "
    "the evaluation scope, and the limitation that bounds the conclusion."
)


def _result(source: str, *, status: str = "success", claim: str = LONG_CLAIM) -> SourceResult:
    claims = []
    if status == "success":
        claims = [EvidenceItem(
            claim=claim,
            source=source,
            verbatim_quote=claim,
            evidence_class="authoritative_document",
            source_identity=f"{source.lower()}-source",
            content_hash=f"hash-{source.lower()}-{claim[:8]}",
            relevance=0.9,
            authority=0.85,
            evidence_refs=[f"[{source}]"],
        )]
    return SourceResult(
        source=source,
        status=status,
        content=claim if status == "success" else "No evidence.",
        claims=claims,
        evidence_class="authoritative_document",
    )


class _Tool:
    def __init__(self, source: str, results: list[SourceResult]):
        self.source = source
        self.results = list(results)
        self.queries: list[str] = []

    def invoke(self, payload: dict) -> str:
        self.queries.append(payload["query"])
        result = self.results.pop(0) if self.results else _result(self.source, status="no_evidence")
        return result.to_tool_text()


def test_ledger_deduplicates_content_but_keeps_visibility_and_subquestion_binding():
    ledger = EvidenceLedger("run-test")
    result = _result("RAG")
    ledger.append_source_result(result, subquestion_id="sq-1", query_id="q-1")
    ledger.append_source_result(result, subquestion_id="sq-2", query_id="q-2")
    ledger.append_source_result(
        result,
        subquestion_id="sq-1",
        query_id="q-3",
        visibility="verification_only",
    )

    assert len(ledger.records) == 2
    primary = [item for item in ledger.records.values() if item.visibility == "primary"]
    assert primary[0].subquestion_ids == ["sq-1", "sq-2"]
    snapshot = ledger.freeze("round_0")
    assert isinstance(snapshot.records, tuple)
    assert len(snapshot.primary_records()) == 1
    assert len([item for item in snapshot.records if item.visibility == "verification_only"]) == 1


def test_round0_retrieves_each_subquestion_independently():
    state = _new_state("main question")
    state["_sub_questions"] = [
        {"id": "sq-1", "question": "first", "search_queries": ["query-one"]},
        {"id": "sq-2", "question": "second", "search_queries": ["query-two"]},
    ]
    rag = _Tool("RAG", [_result("RAG"), _result("RAG")])
    web = _Tool("Web", [_result("Web"), _result("Web")])

    result = retrieve_node(state, rag, web)

    assert sorted(rag.queries) == ["query-one", "query-two"]
    assert sorted(web.queries) == ["query-one", "query-two"]
    assert set(result["_round0_results"]) == {"sq-1", "sq-2"}
    assert {
        subquestion_id
        for record in result["_evidence_ledger"]["records"]
        for subquestion_id in record["subquestion_ids"]
    } == {"sq-1", "sq-2"}


def test_barrier_runs_one_bounded_verification_only_correction_round():
    state = _new_state("main question")
    state["_sub_questions"] = [
        {"id": "sq-1", "question": "critical question", "importance": "high", "search_queries": ["query"]},
    ]
    rag = _Tool("RAG", [_result("RAG", status="no_evidence")])
    web = _Tool("Web", [_result("Web", status="no_evidence"), _result("Web")])

    round0 = retrieve_node(state, rag, web)
    barrier = barrier_node({**state, **round0})
    assert len(barrier["_correction_actions"]) == 1
    assert barrier["_correction_actions"][0]["trigger"] == "critical_claim_uncovered"

    corrected = correction_node({**state, **round0, **barrier}, rag, web)
    records = corrected["_ledger_snapshot"]["records"]
    assert corrected["_correction_round"] == 1
    assert len([item for item in records if item["visibility"] == "verification_only"]) == 1
    assert corrected["_citation_map"] == {}
    assert len(web.queries) == 2

    second = correction_node({**state, **round0, **barrier, **corrected}, rag, web)
    assert second["_pipeline_stage"] == "correction_skipped"
    assert len(web.queries) == 2
