"""Repeatable P1.5 representative-set and blind-review evaluation."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import PROJECT_ROOT


DEFAULT_CASES_PATH = PROJECT_ROOT / "evaluation" / "generalized_research_representative_set.json"
RUBRIC_DIMENSIONS = (
    "factual_citation_match",
    "scope_and_coverage",
    "mechanism_rigor",
    "quantitative_and_implementation_detail",
    "comparative_synthesis",
    "decision_value",
)
PAIRWISE_DIMENSIONS = ("breadth", "depth", "evidence_correctness", "synthesis_insight")


def load_representative_cases(path: str | Path | None = None) -> list[dict[str, Any]]:
    source = Path(path) if path else DEFAULT_CASES_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    cases = [dict(item) for item in payload.get("cases") or [] if isinstance(item, dict)]
    _validate_case_set(cases)
    return cases


def build_run_record(
    case: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize one run summary into the durable WP7 evaluation record."""

    delivery = dict(summary.get("delivery_assessment") or {})
    delivery_status = str(
        summary.get("delivery_status") or delivery.get("status") or "diagnostic_only"
    )
    report_paths = [
        str(summary.get(key) or "")
        for key in ("report_md_path", "report_html_path", "report_evidence_path")
    ]
    diagnostic_paths = [
        str(summary.get(key) or "")
        for key in ("diagnostic_markdown_path", "diagnostic_html_path", "diagnostic_evidence_path")
    ]
    deterministic_failures: list[str] = []
    if delivery_status == "diagnostic_only" and any(report_paths):
        deterministic_failures.append("diagnostic_artifact_exposed_as_formal_report")
    if delivery_status in {"deliverable", "limited"} and not str(summary.get("report_md_path") or ""):
        deterministic_failures.append("formal_report_path_missing")
    invalid_citations = int((delivery.get("metrics") or {}).get("invalid_citation_count") or 0)
    if invalid_citations:
        deterministic_failures.append("invalid_citations")
    off_domain = int(
        (delivery.get("metrics") or {}).get("off_domain_evidence_in_report")
        or summary.get("off_domain_evidence_in_report")
        or 0
    )
    if off_domain:
        deterministic_failures.append("off_domain_evidence_in_formal_report")
    token_runtime = dict(
        ((summary.get("model_trace") or {}).get("token_budget_runtime") or {})
    )
    return {
        "case_id": str(case.get("id") or ""),
        "query": str(case.get("query") or summary.get("query") or ""),
        "domain": str(case.get("domain") or ""),
        "category": str(case.get("category") or ""),
        "rag_condition": str(case.get("rag_condition") or "available"),
        "run_id": str(summary.get("run_id") or ""),
        "provider_models": dict((summary.get("model_trace") or {}).get("roles") or {}),
        "elapsed_ms": float(summary.get("elapsed_ms") or 0.0),
        "token_runtime": token_runtime,
        "estimated_cost": summary.get("estimated_cost"),
        "delivery_status": delivery_status,
        "delivery_gate": delivery,
        "factcheck_status": str(summary.get("factcheck_status") or ""),
        "formal_artifacts": [item for item in report_paths if item],
        "diagnostic_artifacts": [item for item in diagnostic_paths if item],
        "warnings": [str(item) for item in summary.get("warnings") or []],
        "deterministic_failures": deterministic_failures,
        "deterministic_passed": not deterministic_failures,
        "off_domain_evidence_in_report": off_domain,
    }


def evaluate_batch(
    records: Iterable[Mapping[str, Any]],
    blind_reviews: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    runs = [dict(item) for item in records]
    reviews = [dict(item) for item in blind_reviews]
    statuses = [str(item.get("delivery_status") or "") for item in runs]
    deliverable_count = statuses.count("deliverable")
    limited_count = statuses.count("limited")
    diagnostic_count = len(runs) - deliverable_count - limited_count
    deterministic_passed = all(bool(item.get("deterministic_passed")) for item in runs)
    no_off_domain = all(int(item.get("off_domain_evidence_in_report") or 0) == 0 for item in runs)

    medians = {
        dimension: _median_score(reviews, dimension)
        for dimension in RUBRIC_DIMENSIONS
    }
    active_medians = [value for value in medians.values() if value is not None]
    overall_median = statistics.median(active_medians) if active_medians else 0.0
    pairwise = {
        dimension: _pairwise_median(reviews, dimension)
        for dimension in PAIRWISE_DIMENSIONS
    }
    p15_wins = sum(value > 0 for value in pairwise.values())
    p15_regressions = sum(value < 0 for value in pairwise.values())
    complete_case_set = len(runs) == 12 and len({item.get("case_id") for item in runs}) == 12
    reviews_complete = len(reviews) >= 12 and all(value is not None for value in medians.values())
    passed = bool(
        complete_case_set
        and deterministic_passed
        and no_off_domain
        and deliverable_count >= 10
        and limited_count <= 2
        and diagnostic_count == 0
        and reviews_complete
        and overall_median >= 4.0
        and all(float(value or 0.0) >= 3.0 for value in medians.values())
        and p15_wins >= 3
        and p15_regressions == 0
    )
    failures: list[str] = []
    if not complete_case_set:
        failures.append("representative_set_incomplete")
    if not deterministic_passed:
        failures.append("deterministic_gate_failed")
    if not no_off_domain:
        failures.append("off_domain_evidence_entered_formal_report")
    if deliverable_count < 10 or limited_count > 2 or diagnostic_count:
        failures.append("delivery_exit_line_not_met")
    if not reviews_complete:
        failures.append("blind_reviews_incomplete")
    elif overall_median < 4.0 or any(float(value or 0.0) < 3.0 for value in medians.values()):
        failures.append("blind_review_quality_below_exit_line")
    if reviews_complete and (p15_wins < 3 or p15_regressions):
        failures.append("p1_pairwise_comparison_below_exit_line")
    return {
        "passed": passed,
        "run_count": len(runs),
        "deliverable_count": deliverable_count,
        "limited_count": limited_count,
        "diagnostic_count": diagnostic_count,
        "deterministic_passed": deterministic_passed,
        "no_off_domain_evidence": no_off_domain,
        "blind_review_medians": medians,
        "blind_review_overall_median": overall_median,
        "pairwise_medians": pairwise,
        "p15_pairwise_wins": p15_wins,
        "p15_pairwise_regressions": p15_regressions,
        "failures": failures,
    }


def consecutive_batches_reach_exit_line(batches: Iterable[Mapping[str, Any]]) -> bool:
    results = [dict(item) for item in batches]
    return len(results) >= 3 and all(bool(item.get("passed")) for item in results[-3:])


def _validate_case_set(cases: list[dict[str, Any]]) -> None:
    if len(cases) != 12:
        raise ValueError(f"representative set must contain 12 cases, found {len(cases)}")
    identifiers = [str(item.get("id") or "") for item in cases]
    if any(not item for item in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("representative cases require unique non-empty ids")
    required = {"id", "query", "domain", "category", "rag_condition"}
    for item in cases:
        missing = required - set(item)
        if missing:
            raise ValueError(f"case {item.get('id')!r} missing fields: {sorted(missing)}")


def _median_score(reviews: list[dict[str, Any]], dimension: str) -> float | None:
    values = [
        float((item.get("scores") or {}).get(dimension))
        for item in reviews
        if (item.get("scores") or {}).get(dimension) is not None
    ]
    return round(float(statistics.median(values)), 3) if values else None


def _pairwise_median(reviews: list[dict[str, Any]], dimension: str) -> float:
    values = [
        float((item.get("p1_comparison") or {}).get(dimension))
        for item in reviews
        if (item.get("p1_comparison") or {}).get(dimension) is not None
    ]
    return round(float(statistics.median(values)), 3) if values else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate P1.5 representative research runs")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--summary", action="append", default=[], metavar="CASE_ID=PATH")
    parser.add_argument("--blind-reviews", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--list-cases", action="store_true")
    args = parser.parse_args(argv)
    cases = load_representative_cases(args.cases)
    if args.list_cases:
        print(json.dumps({"cases": cases, "rubric": RUBRIC_DIMENSIONS}, ensure_ascii=False, indent=2))
        return 0
    by_id = {str(item["id"]): item for item in cases}
    records = []
    for value in args.summary:
        case_id, separator, path = value.partition("=")
        if not separator or case_id not in by_id:
            parser.error("--summary must use CASE_ID=PATH with a known case id")
        summary = json.loads(Path(path).read_text(encoding="utf-8"))
        records.append(build_run_record(by_id[case_id], summary))
    reviews = []
    if args.blind_reviews:
        reviews_payload = json.loads(Path(args.blind_reviews).read_text(encoding="utf-8"))
        reviews = [dict(item) for item in reviews_payload.get("reviews") or []]
    result = {"records": records, "batch": evaluate_batch(records, reviews)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if result["batch"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
