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


# ============================================================
# Query-level semantic Gold (reusable across runs)
# ============================================================


def _semantic_asset() -> dict:
    return {
        "schema_version": "conflux-v2-gold-semantic-v1",
        "case_id": "sem-case",
        "query": "query",
        "negative_semantics": ["provide your assessment", "ingestion_action:"],
        "aspects": [
            {
                "aspect_id": "asp-1",
                "aspect": "experiments show RAG reduces hallucination",
                "keywords": ["benchmark", "reduces hallucination", "实验", "基准"],
                "positive_semantics": ["grounding generation on retrieved evidence reduces hallucinations"],
                "expected_policy": "verify",
            },
            {
                "aspect_id": "asp-2",
                "aspect": "mechanisms of RAG",
                "keywords": ["mechanism", "external knowledge"],
                "positive_semantics": ["combining them with external knowledge sources"],
                "expected_policy": "abstain",
            },
        ],
        "answer": {"run_status": "completed", "confidence": "medium", "factcheck_status": "passed"},
    }


def _semantic_summary(tmp_path) -> dict:
    trace = tmp_path / "run.trace.jsonl"
    trace.write_text(
        '{"stage": "v2_run_summary", "metadata": {"query_plan": [{"id": "sq-1", "question": "有哪些实验或基准测试表明 RAG 能减少大模型幻觉？"}]}}\n',
        encoding="utf-8",
    )
    return {
        "query": "query",
        "gold_case_id": "sem-case",
        "run_status": "completed",
        "confidence": "medium",
        "factcheck_status": "passed",
        "trace_path": str(trace),
        "ledger_snapshot": {"records": [
            {"evidence_id": "r:ev-1", "subquestion_id": "sq-1", "visibility": "primary",
             "claim_fitness": 0.9, "verbatim_quote": "Provide your assessment in the following JSON format."},
            {"evidence_id": "r:ev-2", "subquestion_id": "sq-1", "visibility": "primary",
             "claim_fitness": 0.8, "verbatim_quote": "Grounding generation on retrieved evidence reduces hallucinations in benchmarks."},
        ]},
        "claim_records": [
            {"claim_id": "c-1", "evidence_ids": ["r:ev-1"],
             "verification_result": {"verdict": "supports"}, "text": "x"},
            {"claim_id": "c-2", "evidence_ids": ["r:ev-2"],
             "verification_result": {"verdict": "supports"}, "text": "grounding generation on retrieved evidence reduces hallucinations"},
        ],
        "invalid_citation_count": 0,
        "budget_consumed": {"input_tokens": 10, "output_tokens": 5},
    }


def test_semantic_gold_asset_is_loadable():
    from conflux.evaluation_gold import load_semantic_gold
    assets = load_semantic_gold("evaluation/v2_gold")
    assert any(item["case_id"] == "rag-hallucination-verification" for item in assets)


def test_semantic_score_marks_negative_evidence_cited_as_support(tmp_path):
    from conflux.evaluation_gold import score_run_semantic
    summary = _semantic_summary(tmp_path)
    result = score_run_semantic("run-label", summary, [_semantic_asset()])
    verification = result["verification"]
    assert verification["verdict_accuracy"] == 0.5
    assert len(verification["negative_evidence_cited_as_support"]) == 1
    assert verification["negative_evidence_cited_as_support"][0]["evidence_id"] == "r:ev-1"
    assert result["answer"]["run_status_match"] is True
    assert result["answer"]["factcheck_match"] is True


def test_semantic_retrieval_grades_negative_as_zero(tmp_path):
    from conflux.evaluation_gold import score_run_semantic
    summary = _semantic_summary(tmp_path)
    result = score_run_semantic("run-label", summary, [_semantic_asset()])
    row = result["retrieval"][0]
    assert row["aspect_id"] == "asp-1"
    assert row["aligned_subquestion_id"] == "sq-1"
    assert row["irrelevant_at_k"] == 1  # ev-1 is negative; ev-2 is positive


def test_semantic_aspect_coverage_counts_keyword_hits(tmp_path):
    from conflux.evaluation_gold import score_run_semantic

    summary = _semantic_summary(tmp_path)
    summary["claim_records"][1]["text"] = "基准测试表明 RAG 能减少幻觉"
    result = score_run_semantic("run-label", summary, [_semantic_asset()])
    coverage = result["answer"]["aspect_coverage"]
    detail = result["answer"]["aspect_coverage_detail"]["asp-1"]
    assert coverage["asp-1"] is True
    assert "基准" in detail["keywords"]
    assert detail["exact_positive_semantics"] == []
    assert coverage["asp-2"] is False


def test_semantic_aspect_coverage_detail_lists_exact_hits(tmp_path):
    from conflux.evaluation_gold import score_run_semantic

    summary = _semantic_summary(tmp_path)
    result = score_run_semantic("run-label", summary, [_semantic_asset()])
    detail = result["answer"]["aspect_coverage_detail"]["asp-1"]
    assert detail["exact_positive_semantics"] == [
        "grounding generation on retrieved evidence reduces hallucinations"
    ]


def test_generation_prompts_require_coverage_and_recommendations():
    from conflux.graph_v2 import DECOMPOSE_PROMPT
    from conflux.research_prompts import CLAIM_GENERATION_PROMPT

    assert "Cover at least three distinct aspects" in CLAIM_GENERATION_PROMPT
    assert "recommendation or trade-off" in CLAIM_GENERATION_PROMPT
    assert "无法通过增加检索或外部证据解决" in DECOMPOSE_PROMPT
    assert "比较与权衡" in DECOMPOSE_PROMPT
