"""§8.10 Gold schema and offline scoring tests."""

from __future__ import annotations

from conflux.evaluation_gold import (
    GOLD_SCHEMA_VERSION,
    load_gold_bundle,
    score_run,
    validate_gold_bundle,
)


def _bundle() -> dict:
    return {
        "manifest": {"schema_version": GOLD_SCHEMA_VERSION},
        "retrieval": [{
            "case_id": "case-1",
            "subquestions": [{
                "subquestion_id": "sq-1",
                "k": 2,
                "evidence": [
                    {"evidence_id": "e-1", "relevance_grade": 3},
                    {"evidence_id": "e-2", "relevance_grade": 0},
                ],
            }],
        }],
        "verification": [{
            "case_id": "case-1",
            "subquestions": [{
                "subquestion_id": "sq-1",
                "expected_claim_policy": "abstain",
                "evidence": [{"evidence_id": "e-1", "verdict": "supports"}],
            }],
        }],
        "answer": [{
            "case_id": "case-1",
            "expected": {"run_status": "partial", "confidence": "low"},
            "expected_claims": [],
        }],
    }


def test_repository_gold_bundle_is_valid():
    bundle = load_gold_bundle("evaluation/v2_gold")
    assert bundle["manifest"]["schema_version"] == GOLD_SCHEMA_VERSION
    assert bundle["retrieval"][0]["case_id"] == "evidenceledger-limitations-smoke"


def test_invalid_gold_grade_is_rejected():
    bundle = _bundle()
    bundle["retrieval"][0]["subquestions"][0]["evidence"][0]["relevance_grade"] = 4
    assert any("invalid relevance_grade" in error for error in validate_gold_bundle(bundle))


def test_score_run_separates_direct_recall_from_related_context():
    summary = {
        "query": "question",
        "run_status": "partial",
        "confidence": "low",
        "ledger_snapshot": {
            "records": [
                {"evidence_id": "e-1", "subquestion_id": "sq-1", "visibility": "primary"},
                {"evidence_id": "e-2", "subquestion_id": "sq-1", "visibility": "primary"},
            ]
        },
        "claim_records": [],
        "factcheck_status": "skipped",
        "budget_consumed": {"input_tokens": 10, "output_tokens": 5},
    }
    result = score_run("case-1", summary, _bundle())
    retrieval = result["retrieval"][0]
    assert retrieval["recall_at_k"] == 1.0
    assert retrieval["direct_recall_at_k"] == 1.0
    assert retrieval["ndcg_at_k"] == 1.0
    assert result["verification"]["abstention_correct"] is True
    assert result["runtime"]["total_tokens"] == 15


def test_unscored_verdict_labels_are_reported_but_do_not_reduce_accuracy():
    bundle = _bundle()
    bundle["verification"][0]["subquestions"][0]["evidence"].append({
        "evidence_id": "e-2",
        "verdict": "contradicts",
        "score_verdict": False,
    })
    summary = {
        "query": "question",
        "run_status": "partial",
        "confidence": "low",
        "ledger_snapshot": {"records": [{"evidence_id": "e-1", "subquestion_id": "sq-1"}]},
        "claim_records": [{
            "claim_id": "claim-1",
            "evidence_ids": ["e-1"],
            "verification_result": {"verdict": "supports"},
            "generation_attribution": {"citation_refs": ["[1]"]},
        }],
        "factcheck_status": "skipped",
    }
    result = score_run("case-1", summary, bundle)
    assert result["verification"]["verdict_accuracy"] == 1.0
    assert result["verification"]["unscored_label_count"] == 1
