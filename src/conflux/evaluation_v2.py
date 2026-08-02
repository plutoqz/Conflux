"""V2 评测框架 —— 适配 answer_first 管道的评估与 A/B 对比。

与 P1.5 评测（research_evaluation.py）的关键区别：
- 不要求 deliverable/limited/diagnostic_only 三态门禁
- 使用正交状态模型（run_status, report_available, confidence）
- 确定性门禁仅检查基本结构完整性和引用合法性
- 盲评关注内容质量而非形式合规

用法：
  python -m conflux.evaluation_v2 --baseline batch.json --v2 batch.json --output comparison.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import PROJECT_ROOT
from .p1_evaluation import (
    PAIRWISE_SYSTEM,
    _bounded_score,
    deterministic_output_rubric,
)
from .research_evaluation import (
    DEFAULT_CASES_PATH,
    PAIRWISE_DIMENSIONS,
    RUBRIC_DIMENSIONS,
    load_representative_cases,
)

# V2 评审复用 p1_evaluation 的中文评审者身份；维度保留 V2 六维定义，
# 以保证与历史盲评批次的评分语义一致。
V2_REVIEW_DIMENSIONS = RUBRIC_DIMENSIONS
V2_DIMENSION_DESCRIPTIONS = {
    "factual_citation_match": "事实与引用匹配度：声明是否有外部来源支撑，引用是否可追溯",
    "scope_and_coverage": "范围与覆盖面：是否涵盖问题的关键维度，有无重大遗漏",
    "mechanism_rigor": "机制分析严谨度：是否解释了形成机制/因果关系，而非仅罗列现象",
    "quantitative_and_implementation_detail": "定量与实现细节：是否包含数据、实例或实现层面信息",
    "comparative_synthesis": "比较综合能力：是否做了跨维度/跨来源的综合比较",
    "decision_value": "决策参考价值：对研究者/实践者是否有可行动的洞察",
}

# V2 确定性门禁 —— 只检查基本完整性，不检查覆盖率/门禁
V2_DETERMINISTIC_CHECKS = (
    "report_not_empty",        # 至少有正文
    "no_invalid_citations",    # 引用标号均在来源集合中
    "no_missing_required_sections",  # 必须包含：直接回答、至少一节正文、可信度说明
    "no_off_domain_evidence",  # 错域证据未进入正式报告
)


def build_v2_run_record(
    case: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    """从 V2 管道运行摘要构建评测记录。"""
    run_status = str(summary.get("run_status") or "failed")
    report_available = bool(summary.get("report_available"))
    confidence = str(summary.get("confidence") or "unverified")

    # 确定性检查
    failures: list[str] = []
    report_text = str(summary.get("report_markdown") or "")
    if not report_text.strip():
        failures.append("report_not_empty")
    invalid_citations = int(summary.get("invalid_citation_count") or 0)
    if invalid_citations:
        failures.append("no_invalid_citations")
    missing_sections = bool(summary.get("missing_required_sections"))
    if missing_sections:
        failures.append("no_missing_required_sections")
    off_domain = int(summary.get("off_domain_evidence_in_report") or 0)
    if off_domain:
        failures.append("no_off_domain_evidence")

    return {
        "case_id": str(case.get("id") or ""),
        "query": str(case.get("query") or summary.get("query") or ""),
        "domain": str(case.get("domain") or ""),
        "category": str(case.get("category") or ""),
        "rag_condition": str(case.get("rag_condition") or "available"),
        "run_id": str(summary.get("run_id") or ""),
        "run_status": run_status,
        "report_available": report_available,
        "confidence": confidence,
        "elapsed_ms": float(summary.get("elapsed_ms") or 0.0),
        "section_count": int(summary.get("section_count") or 0),
        "external_evidence_count": int(summary.get("external_evidence_count") or 0),
        "analysis_only_count": int(summary.get("analysis_only_count") or 0),
        "report_length_chars": len(report_text),
        "deterministic_failures": failures,
        "deterministic_passed": not failures,
    }


def build_v2_review_prompt(
    query: str,
    report: str,
    *,
    evaluation_date: str | None = None,
) -> str:
    """构建 V2 单侧盲评 prompt —— 复用 p1_evaluation 的中文评审者身份。

    评分维度沿用 V2 六维（RUBRIC_DIMENSIONS），与历史盲评批次语义一致；
    评审者身份、输出约束和证据审计规则复用 p1_evaluation.PAIRWISE_SYSTEM。
    """
    from datetime import date

    dim_parts = []
    for dim in V2_REVIEW_DIMENSIONS:
        desc = V2_DIMENSION_DESCRIPTIONS.get(dim, dim)
        dim_parts.append(f"  - {dim}：{desc}")
    max_chars = 12000
    body = str(report or "")
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[... report truncated ...]"
    return f"""{PAIRWISE_SYSTEM}

评测日期：{evaluation_date or date.today().isoformat()}。不得把该日期之前已发布的材料误判为未来来源。
研究问题：{query}

报告正文：
{body}

## 评审要求

逐项使用 1-5 分（整数）：
{chr(10).join(dim_parts)}

仅输出以下 JSON：
{{"scores":{{"factual_citation_match":3,"scope_and_coverage":3,"mechanism_rigor":3,
"quantitative_and_implementation_detail":3,"comparative_synthesis":3,"decision_value":3}},
"overall":3.0,"reason":"brief comment","is_empty":false}}

约束：
- 报告正文不足 200 字符时 is_empty=true 且各维度 1 分。
- 明确标注为"模型分析/分析判断"的内容应按逻辑与推断强度评分，不因缺少外部引用判为事实错误。
- 不得凭模型记忆、编号观感或来源知名度断言来源虚构。"""


def normalize_v2_review(payload: dict[str, Any]) -> dict[str, Any]:
    """校验 V2 单侧盲评输出边界 —— 复用 p1_evaluation 的分数归一化。"""
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scores = {
        dim: _bounded_score(raw_scores.get(dim))
        for dim in V2_REVIEW_DIMENSIONS
    }
    overall = payload.get("overall")
    try:
        overall = float(overall)
    except (TypeError, ValueError):
        overall = 0.0
    # 与历史盲评语义一致：overall 缺失或为 0 时退化为六维平均分。
    if overall <= 0.0:
        overall = round(sum(scores.values()) / len(scores), 1) if scores else 1.0
    overall = max(1.0, min(5.0, overall))
    return {
        "scores": scores,
        "overall": round(overall, 1),
        "reason": str(payload.get("reason") or "")[:500],
        "is_empty": bool(payload.get("is_empty", False)),
    }


def v2_deterministic_rubric(
    report: str,
    required_dimensions: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """V2 报告的确定性输出检查 —— 直接复用 p1_evaluation 实现。"""
    return deterministic_output_rubric(report, required_dimensions)


def evaluate_v2_batch(
    records: Iterable[Mapping[str, Any]],
    blind_reviews: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """V2 批次评测 —— 关注 run_status + confidence，不要求固定交付门禁。"""
    runs = [dict(item) for item in records]
    reviews = [dict(item) for item in blind_reviews]

    run_statuses = [str(item.get("run_status") or "") for item in runs]
    completed = run_statuses.count("completed")
    partial = run_statuses.count("partial")
    failed = run_statuses.count("failed")

    confidences = [str(item.get("confidence") or "") for item in runs]
    high_count = confidences.count("high")
    medium_count = confidences.count("medium")
    low_count = confidences.count("low")
    unverified_count = confidences.count("unverified")

    report_available_count = sum(1 for item in runs if bool(item.get("report_available")))
    deterministic_passed = all(bool(item.get("deterministic_passed")) for item in runs)
    complete_case_set = len(runs) == 12 and len({item.get("case_id") for item in runs}) == 12

    # 盲评中位数
    medians = {
        dimension: _median_v2(reviews, dimension)
        for dimension in RUBRIC_DIMENSIONS
    }
    active_medians = [value for value in medians.values() if value is not None]
    overall_median = statistics.median(active_medians) if active_medians else 0.0

    # 与 P1.5 基线的成对比较
    pairwise = {
        dimension: _pairwise_v2(reviews, dimension)
        for dimension in PAIRWISE_DIMENSIONS
    }
    v2_wins = sum(value > 0 for value in pairwise.values())
    v2_regressions = sum(value < 0 for value in pairwise.values())

    # 内容质量聚合指标
    avg_length = (
        statistics.mean([int(item.get("report_length_chars") or 0) for item in runs])
        if runs else 0
    )
    avg_sections = (
        statistics.mean([int(item.get("section_count") or 0) for item in runs])
        if runs else 0
    )
    avg_ext_evidence = (
        statistics.mean([int(item.get("external_evidence_count") or 0) for item in runs])
        if runs else 0
    )

    reviews_complete = len(reviews) >= 12 and all(value is not None for value in medians.values())

    return {
        "run_count": len(runs),
        "completed_count": completed,
        "partial_count": partial,
        "failed_count": failed,
        "report_available_count": report_available_count,
        "confidence_high": high_count,
        "confidence_medium": medium_count,
        "confidence_low": low_count,
        "confidence_unverified": unverified_count,
        "deterministic_passed": deterministic_passed,
        "complete_case_set": complete_case_set,
        "avg_report_length": avg_length,
        "avg_sections": avg_sections,
        "avg_external_evidence": avg_ext_evidence,
        "blind_review_medians": medians,
        "blind_review_overall_median": overall_median,
        "pairwise_medians": pairwise,
        "v2_pairwise_wins": v2_wins,
        "v2_pairwise_regressions": v2_regressions,
        "reviews_complete": reviews_complete,
    }


def compare_batches(
    baseline: dict[str, Any],
    v2: dict[str, Any],
) -> dict[str, Any]:
    """对比 P1.5 基线和 V2 批次。"""
    baseline_diagnostic = baseline.get("diagnostic_count", 0)
    v2_report_available = v2.get("report_available_count", 0)

    return {
        "p15_baseline": {
            "deliverable": baseline.get("deliverable_count", 0),
            "limited": baseline.get("limited_count", 0),
            "diagnostic": baseline_diagnostic,
        },
        "v2": {
            "completed": v2.get("completed_count", 0),
            "partial": v2.get("partial_count", 0),
            "failed": v2.get("failed_count", 0),
            "report_available": v2_report_available,
            "confidence_high": v2.get("confidence_high", 0),
        },
        "delivery_rate_delta": (
            f"{baseline_diagnostic} diagnostic → {v2_report_available} report_available"
        ),
        "avg_length_delta": (
            f"{baseline.get('avg_report_length', 0):.0f} → "
            f"{v2.get('avg_report_length', 0):.0f} chars"
        ),
        "pairwise_wins": v2.get("v2_pairwise_wins", 0),
        "pairwise_regressions": v2.get("v2_pairwise_regressions", 0),
    }


def _median_v2(reviews: list[dict[str, Any]], dimension: str) -> float | None:
    values = [
        float((item.get("scores") or {}).get(dimension))
        for item in reviews
        if (item.get("scores") or {}).get(dimension) is not None
    ]
    return round(float(statistics.median(values)), 3) if values else None


def _pairwise_v2(reviews: list[dict[str, Any]], dimension: str) -> float:
    values = [
        float((item.get("p1_comparison") or {}).get(dimension))
        for item in reviews
        if (item.get("p1_comparison") or {}).get(dimension) is not None
    ]
    return round(float(statistics.median(values)), 3) if values else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate V2 answer_first research runs")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--summary", action="append", default=[], metavar="CASE_ID=PATH")
    parser.add_argument("--blind-reviews", default="")
    parser.add_argument("--baseline", default="", help="P1.5 baseline batch JSON for comparison")
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
        records.append(build_v2_run_record(by_id[case_id], summary))
    blind_reviews = []
    if args.blind_reviews:
        blind_reviews = json.loads(Path(args.blind_reviews).read_text(encoding="utf-8"))
    result = evaluate_v2_batch(records, blind_reviews)
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        comparison = compare_batches(baseline, result)
        result["p15_comparison"] = comparison
    output_path = Path(args.output) if args.output else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
