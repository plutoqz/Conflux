from __future__ import annotations

import json
from collections import Counter

from conflux.research_evaluation import (
    PAIRWISE_DIMENSIONS,
    RUBRIC_DIMENSIONS,
    build_run_record,
    consecutive_batches_reach_exit_line,
    evaluate_batch,
    load_representative_cases,
    main,
)


def test_representative_set_has_required_mix_and_domains() -> None:
    cases = load_representative_cases()
    categories = Counter(item["category"] for item in cases)

    assert len(cases) == 12
    assert categories == {
        "broad_review_or_limitations": 3,
        "technical_comparison_or_design": 3,
        "causal_mechanism_or_evidence_review": 2,
        "recent_status": 2,
        "rag_empty_web_available": 2,
    }
    assert len({item["domain"] for item in cases}) >= 6


def test_run_record_preserves_diagnostics_and_runtime_telemetry() -> None:
    case = load_representative_cases()[0]
    record = build_run_record(case, {
        "run_id": "run-1",
        "delivery_status": "diagnostic_only",
        "diagnostic_markdown_path": "diagnostics/run-1.md",
        "report_md_path": "",
        "model_trace": {
            "roles": {"planner": {"model": "fixture"}},
            "token_budget_runtime": {"actual_tokens": 80, "charged_tokens": 60},
        },
        "delivery_assessment": {"metrics": {"invalid_citation_count": 0}},
    })

    assert record["deterministic_passed"] is True
    assert record["formal_artifacts"] == []
    assert record["diagnostic_artifacts"] == ["diagnostics/run-1.md"]
    assert record["token_runtime"]["actual_tokens"] == 80


def test_batch_exit_line_and_three_consecutive_batches() -> None:
    cases = load_representative_cases()
    records = []
    reviews = []
    for index, case in enumerate(cases):
        records.append({
            "case_id": case["id"],
            "delivery_status": "deliverable" if index < 10 else "limited",
            "deterministic_passed": True,
            "off_domain_evidence_in_report": 0,
        })
        reviews.append({
            "case_id": case["id"],
            "scores": {dimension: 4 for dimension in RUBRIC_DIMENSIONS},
            "p1_comparison": {
                dimension: (1 if dimension != "depth" else 0)
                for dimension in PAIRWISE_DIMENSIONS
            },
        })

    result = evaluate_batch(records, reviews)

    assert result["passed"] is True
    assert result["p15_pairwise_wins"] == 3
    assert consecutive_batches_reach_exit_line([result, result, result]) is True
    assert consecutive_batches_reach_exit_line([result, {**result, "passed": False}, result]) is False


def test_evaluation_cli_creates_output_parent_directory(tmp_path) -> None:
    case = load_representative_cases()[0]
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({
        "run_id": "run-1",
        "delivery_status": "diagnostic_only",
        "delivery_assessment": {"metrics": {"invalid_citation_count": 0}},
    }), encoding="utf-8")
    output_path = tmp_path / "new" / "batch.json"

    exit_code = main([
        "--summary", f"{case['id']}={summary_path}",
        "--output", str(output_path),
    ])

    assert exit_code == 1
    assert json.loads(output_path.read_text(encoding="utf-8"))["records"][0]["run_id"] == "run-1"
