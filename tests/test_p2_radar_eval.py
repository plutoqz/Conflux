"""P2 Paper Radar evaluation metric tests (synthetic runs)."""

from __future__ import annotations

from conflux.evaluation_p2 import (
    aggregate_p2_results,
    evaluate_p2_run,
    load_p2_labels,
)


def _labels() -> list[dict]:
    return [
        {"query_id": "q", "paper_id": "p-1", "relevance": 3},
        {"query_id": "q", "paper_id": "p-2", "relevance": 2},
        {"query_id": "q", "paper_id": "p-3", "relevance": 1},
        {"query_id": "q", "paper_id": "p-4", "relevance": 0},
    ]


def _run() -> dict:
    return {
        "links": [
            {"paper_identity": {"canonical_id": "p-1"}, "relevance": 0.9},
            {"paper_identity": {"canonical_id": "p-3"}, "relevance": 0.8},
            {"paper_identity": {"canonical_id": "p-2"}, "relevance": 0.7},
            {"paper_identity": {"canonical_id": "p-5"}, "relevance": 0.6},
            {"paper_identity": {"canonical_id": "p-6"}, "relevance": 0.5},
        ],
        "stats": {
            "total_candidates": 10,
            "after_dedup": 8,
            "llm_total_tokens": 5000,
            "llm_elapsed_ms": 36000,
            "elapsed_seconds": 47.8,
            "llm_fallback_count": 1,
            "needs_review": 1,
            "sources_used": ["arxiv"],
            "failed_sources": ["semantic_scholar"],
        },
        "suggestions": [
            {"evidence_refs": ["p1:c0"]},
            {"evidence_refs": []},
            {"evidence_refs": ["abstract"]},
            {"evidence_refs": []},
        ],
    }


def test_retrieval_metrics():
    result = evaluate_p2_run(_run(), _labels())
    retrieval = result["retrieval"]
    assert retrieval["relevant_labeled_count"] == 2
    assert retrieval["recall_at_1"] == 0.5  # p-1 in top-1, 1 of 2 relevant
    assert retrieval["precision_at_1"] == 1.0
    assert retrieval["recall_at_5"] == 1.0  # p-1 and p-2 both linked
    assert retrieval["precision_at_5"] == 0.4  # p-1, p-3, p-2, p-5, p-6 -> 2 relevant
    assert retrieval["linked_relevant_count"] == 2


def test_duplicate_and_analysis_metrics():
    result = evaluate_p2_run(_run(), _labels())
    assert result["duplicate_handling"]["dedup_rate"] == 0.2  # 1 - 8/10
    assert result["analysis"]["ungrounded_analysis_rate"] == 0.5  # 2 of 4
    assert result["analysis"]["llm_fallback_count"] == 1
    assert result["analysis"]["needs_review_count"] == 1


def test_source_error_rate():
    result = evaluate_p2_run(_run(), _labels())
    assert result["sources"]["source_error_rate"] == 0.5  # 1 of 2


def test_aggregate():
    results = [evaluate_p2_run(_run(), _labels()), evaluate_p2_run(_run(), _labels())]
    agg = aggregate_p2_results(results)
    assert agg["run_count"] == 2
    assert agg["retrieval"]["mean_recall_at_5"] == 1.0
    assert agg["retrieval"]["mean_precision_at_5"] == 0.4
    assert agg["analysis"]["total_needs_review"] == 2
    assert agg["analysis"]["total_llm_fallback"] == 2


def test_repository_labels_loadable():
    labels = load_p2_labels("evaluation/p2_radar/labels.jsonl")
    assert len(labels) >= 3
    assert all("relevance" in label for label in labels)
