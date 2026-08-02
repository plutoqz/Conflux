"""V2 评估框架回归测试（阶段 B2）。

覆盖 evaluation_v2 的代表集记录构建、批次统计、评审 prompt 复用
与确定性 rubric，作为改 Pipeline/Prompt 后的回归防守。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conflux.evaluation_v2 import (
    V2_REVIEW_DIMENSIONS,
    build_v2_review_prompt,
    build_v2_run_record,
    compare_batches,
    evaluate_v2_batch,
    normalize_v2_review,
    v2_deterministic_rubric,
)

CASE = {
    "id": "test-case-001",
    "query": "当前研究有哪些关键瓶颈？",
    "domain": "ai",
    "category": "limitations",
    "rag_condition": "available",
}


def _summary(**overrides) -> dict:
    base = {
        "run_id": "run-001",
        "run_status": "completed",
        "report_available": True,
        "confidence": "high",
        "elapsed_ms": 120_000,
        "section_count": 6,
        "external_evidence_count": 8,
        "analysis_only_count": 2,
        "report_markdown": "# 回答\n\n正文内容足够长。" * 50,
        "report_md_path": "reports/run-001.md",
        "invalid_citation_count": 0,
        "missing_required_sections": False,
        "off_domain_evidence_in_report": 0,
    }
    base.update(overrides)
    return base


class TestBuildV2RunRecord:
    def test_completed_record_passes_deterministic_checks(self):
        record = build_v2_run_record(CASE, _summary())
        assert record["run_status"] == "completed"
        assert record["confidence"] == "high"
        assert record["deterministic_passed"] is True
        assert record["deterministic_failures"] == []

    def test_failed_run_flagged(self):
        record = build_v2_run_record(
            CASE,
            _summary(run_status="failed", report_available=False, report_markdown=""),
        )
        assert record["run_status"] == "failed"
        assert record["deterministic_passed"] is False
        assert "report_not_empty" in record["deterministic_failures"]

    def test_empty_report_flagged(self):
        record = build_v2_run_record(CASE, _summary(report_markdown=""))
        assert "report_not_empty" in record["deterministic_failures"]

    def test_invalid_citations_flagged(self):
        record = build_v2_run_record(CASE, _summary(invalid_citation_count=3))
        assert "no_invalid_citations" in record["deterministic_failures"]

    def test_missing_sections_flagged(self):
        record = build_v2_run_record(CASE, _summary(missing_required_sections=True))
        assert "no_missing_required_sections" in record["deterministic_failures"]

    def test_off_domain_evidence_flagged(self):
        record = build_v2_run_record(CASE, _summary(off_domain_evidence_in_report=2))
        assert "no_off_domain_evidence" in record["deterministic_failures"]


class TestEvaluateV2Batch:
    def _records(self, n: int = 12, **overrides) -> list[dict]:
        return [
            build_v2_run_record(
                {**CASE, "id": f"case-{i:03d}"},
                _summary(run_id=f"run-{i}", **overrides),
            )
            for i in range(n)
        ]

    def _reviews(self, n: int = 12, score: float = 4.0) -> list[dict]:
        return [
            {
                "case_id": f"case-{i:03d}",
                "scores": {dim: score for dim in V2_REVIEW_DIMENSIONS},
                "p1_comparison": {dim: 1.0 for dim in ("breadth", "depth", "evidence_correctness", "synthesis_insight")},
            }
            for i in range(n)
        ]

    def test_full_batch_aggregates(self):
        result = evaluate_v2_batch(self._records(), self._reviews())
        assert result["run_count"] == 12
        assert result["completed_count"] == 12
        assert result["failed_count"] == 0
        assert result["confidence_high"] == 12
        assert result["deterministic_passed"] is True
        assert result["complete_case_set"] is True
        assert result["blind_review_overall_median"] == 4.0
        assert result["reviews_complete"] is True
        assert result["v2_pairwise_wins"] == 4

    def test_partial_runs_counted(self):
        records = self._records(12)
        records[0]["run_status"] = "partial"
        records[1]["run_status"] = "failed"
        result = evaluate_v2_batch(records, self._reviews())
        assert result["completed_count"] == 10
        assert result["partial_count"] == 1
        assert result["failed_count"] == 1

    def test_low_scores_reflected_in_median(self):
        result = evaluate_v2_batch(self._records(12), self._reviews(score=2.0))
        assert result["blind_review_overall_median"] == 2.0
        assert result["reviews_complete"] is True

    def test_incomplete_case_set_detected(self):
        result = evaluate_v2_batch(self._records(5), self._reviews(5))
        assert result["complete_case_set"] is False

    def test_empty_inputs(self):
        result = evaluate_v2_batch([], [])
        assert result["run_count"] == 0
        assert result["blind_review_overall_median"] == 0.0
        assert result["reviews_complete"] is False


class TestCompareBatches:
    def test_comparison_shape(self):
        v2 = evaluate_v2_batch(
            [build_v2_run_record({**CASE, "id": f"case-{i:03d}"}, _summary()) for i in range(12)],
            [
                {
                    "scores": {dim: 4.0 for dim in V2_REVIEW_DIMENSIONS},
                    "p1_comparison": {dim: 1.0 for dim in ("breadth", "depth", "evidence_correctness", "synthesis_insight")},
                }
                for _ in range(12)
            ],
        )
        baseline = {
            "deliverable_count": 10,
            "limited_count": 2,
            "diagnostic_count": 0,
            "avg_report_length": 8000,
        }
        comparison = compare_batches(baseline, v2)
        assert "p15_baseline" in comparison
        assert "v2" in comparison
        assert "pairwise_wins" in comparison


class TestV2ReviewPrompt:
    def test_prompt_contains_dimensions_and_query(self):
        prompt = build_v2_review_prompt("某研究问题", "报告正文", evaluation_date="2026-08-02")
        for dim in V2_REVIEW_DIMENSIONS:
            assert dim in prompt
        assert "某研究问题" in prompt
        assert "2026-08-02" in prompt

    def test_prompt_truncates_long_report(self):
        prompt = build_v2_review_prompt("q", "长" * 30_000)
        assert "[... report truncated ...]" in prompt

    def test_normalize_clamps_scores(self):
        normalized = normalize_v2_review({
            "scores": {dim: 9 for dim in V2_REVIEW_DIMENSIONS},
            "overall": 0,
            "reason": "ok",
            "is_empty": False,
        })
        assert all(score == 5 for score in normalized["scores"].values())
        assert normalized["overall"] == 5.0

    def test_normalize_missing_scores_default_one(self):
        normalized = normalize_v2_review({"scores": {}, "overall": None, "reason": "", "is_empty": False})
        assert all(score == 1 for score in normalized["scores"].values())
        assert normalized["overall"] == 1.0


class TestV2DeterministicRubric:
    def test_reuses_p1_implementation(self):
        result = v2_deterministic_rubric(
            "## 回答\n" + "详细内容。" * 100,
            ["正确性", "深度"],
        )
        assert "passed" in result
        assert "breadth" in result
        assert "coverage_ratio" in result
