"""Deterministic quality checks for a completed Conflux run."""

from __future__ import annotations

import json
import re
from typing import Any

from .source_status import EXTERNAL_EVIDENCE_CLASSES


def evaluate_p1_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate P1 answer quality without treating source count as a vote."""

    report = str(state.get("final_answer") or "")
    run_summary = state.get("_run_summary") or {}
    findings = state.get("_factcheck_findings") or {}
    statuses = state.get("_source_statuses") or {}
    evidence = _load_evidence_payload(str(state.get("_evidence_json") or ""))
    nodes = [item for item in evidence.get("nodes") or [] if isinstance(item, dict)]
    external_nodes = [
        item for item in nodes
        if item.get("evidence_class") in EXTERNAL_EVIDENCE_CLASSES
        and item.get("evidence_refs")
        and item.get("verbatim_quote")
        and _source_succeeded(item, statuses)
    ]
    model_nodes = [item for item in nodes if item.get("evidence_class") == "model_inference"]
    invalid_citations = int(findings.get("invalid_citation_count") or 0)
    coverage = float(findings.get("verified_claim_ratio") or 0.0)
    issues = findings.get("issues") or []
    unresolved_high = [
        item for item in issues
        if isinstance(item, dict)
        and item.get("severity") == "high"
        and not item.get("resolved")
    ]

    scores = {
        "研究过程": _score_p1_process(run_summary),
        "回答质量": 1 if str(state.get("_synthesis_status") or "completed") != "completed" else _score_p1_report(report),
        "证据质量": _score_p1_evidence(external_nodes, model_nodes),
        "引用质量": _score_p1_citations(coverage, invalid_citations, external_nodes),
        "核验修订": _score_p1_verification(str(state.get("_factcheck_status") or ""), findings),
    }
    overall = round(sum(scores.values()) / len(scores), 2)
    passed = (
        overall >= 4.0
        and str(state.get("_factcheck_status") or "") == "passed"
        and invalid_citations == 0
        and not unresolved_high
        and bool(report.strip())
    )
    available_sources = [
        source for source in ("RAG", "Web", "Model")
        if str((statuses.get(source) or {}).get("status") or "") == "success"
    ]
    return {
        "scores": scores,
        "overall": overall,
        "passed": passed,
        "available_sources": available_sources,
        "external_evidence_count": len(external_nodes),
        "model_context_count": len(model_nodes),
        "claim_citation_coverage": {
            "ratio": coverage,
            "valid": int(findings.get("valid_citation_count") or 0),
            "invalid": invalid_citations,
        },
        "factcheck_status": state.get("_factcheck_status"),
        "notes": _p1_quality_notes(scores, available_sources, findings),
    }


def evaluate_p15_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate P1.5 runtime contracts without rewarding report length."""

    archetype = state.get("_query_archetype") or {}
    domain_map = state.get("_domain_map") or {}
    budget = state.get("_research_budget") or {}
    matrix = state.get("_coverage_matrix") or {}
    source_plans = [item for item in state.get("_source_plans") or [] if isinstance(item, dict)]
    contracts = [item for item in state.get("_section_contracts") or [] if isinstance(item, dict)]
    drafts = [item for item in state.get("_section_drafts") or [] if isinstance(item, dict)]
    report = str(state.get("final_answer") or "")
    statuses = state.get("_source_statuses") or {}

    dimensions = [item for item in domain_map.get("dimensions") or [] if isinstance(item, dict)]
    dimension_ids = {str(item.get("id") or "") for item in dimensions if str(item.get("id") or "")}
    high_dimension_ids = {
        str(item.get("id") or "")
        for item in dimensions
        if str(item.get("id") or "") and _importance_value(item.get("importance")) >= 0.7
    }
    coverage_rows = [item for item in matrix.get("dimensions") or [] if isinstance(item, dict)]
    coverage_by_id = {
        str(item.get("dimension_id") or ""): item
        for item in coverage_rows
        if str(item.get("dimension_id") or "")
    }
    covered_high = {
        dimension_id
        for dimension_id in high_dimension_ids
        if str((coverage_by_id.get(dimension_id) or {}).get("status") or "") == "covered"
    }
    high_coverage_ratio = (
        len(covered_high) / len(high_dimension_ids)
        if high_dimension_ids
        else float(matrix.get("high_importance_coverage") or 0.0)
    )

    draft_by_section = {
        str(item.get("section_id") or ""): item
        for item in drafts
        if str(item.get("section_id") or "")
    }
    traced_contracts = 0
    for contract in contracts:
        section_id = str(contract.get("id") or "")
        linked = {str(item) for item in contract.get("dimension_ids") or [] if str(item)}
        draft = draft_by_section.get(section_id) or {}
        draft_dimensions = {str(item) for item in draft.get("dimension_ids") or [] if str(item)}
        if section_id and linked and linked <= dimension_ids and linked <= draft_dimensions:
            traced_contracts += 1
    traceability_ratio = traced_contracts / len(contracts) if contracts else 0.0

    source_plan_dimensions = {
        str(item.get("dimension_id") or "")
        for item in source_plans
        if str(item.get("dimension_id") or "")
    }
    routing_ratio = len(dimension_ids & source_plan_dimensions) / len(dimension_ids) if dimension_ids else 0.0
    failed_sources = {
        source
        for source in ("RAG", "Web")
        if str((statuses.get(source) or {}).get("status") or "")
        in {"failed", "no_evidence", "low_relevance", "fallback", "disabled"}
    }
    failed_source_leak = any(
        marker in report
        for source in failed_sources
        for marker in (("[RAG:" if source == "RAG" else "[Web:"),)
    )

    section_title_hits = sum(
        bool(str(item.get("title") or "").strip())
        and str(item.get("title") or "").strip() in report
        for item in contracts
    )
    section_report_ratio = section_title_hits / len(contracts) if contracts else 0.0
    uncovered = [
        item for item in coverage_rows
        if str(item.get("status") or "") in {"partial", "evidence_scarce", "conflicting"}
    ]
    gap_disclosed = not uncovered or any(
        marker in report for marker in ("未覆盖", "证据不足", "待核验", "争议", "缺口")
    )

    hard_limits = budget.get("global_hard_limits") or {}
    budget_within_hard_limits = all(
        int(budget.get(field) or 0) <= int(limit)
        for field, limit in {
            "major_dimension_limit": hard_limits.get("major_dimension_limit"),
            "evidence_limit": hard_limits.get("evidence_limit"),
            "max_gap_iterations": hard_limits.get("max_gap_iterations"),
            "total_output_chars": hard_limits.get("total_output_chars"),
        }.items()
        if limit not in (None, "")
    )

    protocol_complete = bool(
        archetype.get("type")
        and dimensions
        and budget
        and coverage_rows
        and contracts
        and drafts
    )
    external_unavailable = failed_sources == {"RAG", "Web"}
    coverage_target = float(matrix.get("target") or 0.6)
    coverage_ok = high_coverage_ratio >= min(0.8, max(0.5, coverage_target)) or external_unavailable
    scores = {
        "协议完整性": 5 if protocol_complete else 2,
        "维度覆盖": 5 if high_coverage_ratio >= 0.8 else 4 if coverage_ok else 2,
        "来源路由": 5 if routing_ratio >= 1.0 and not failed_source_leak else 4 if routing_ratio >= 0.8 and not failed_source_leak else 2,
        "章节追溯": 5 if traceability_ratio >= 1.0 else 4 if traceability_ratio >= 0.8 else 2,
        "动态报告契约": 5 if section_report_ratio >= 0.9 and gap_disclosed else 4 if section_report_ratio >= 0.75 and gap_disclosed else 2,
        "预算硬上限": 5 if budget_within_hard_limits else 1,
    }
    passed = (
        protocol_complete
        and coverage_ok
        and routing_ratio >= 0.8
        and traceability_ratio >= 0.8
        and section_report_ratio >= 0.75
        and gap_disclosed
        and budget_within_hard_limits
        and not failed_source_leak
    )
    notes = [f"{name}低于达标线：{score}/5" for name, score in scores.items() if score < 4]
    if failed_source_leak:
        notes.append("失败或无证据来源仍出现在事实引用中。")
    if uncovered and not gap_disclosed:
        notes.append("覆盖矩阵存在未完成维度，但主报告没有一致披露。")
    return {
        "scores": scores,
        "overall": round(sum(scores.values()) / len(scores), 2),
        "passed": passed,
        "protocol_complete": protocol_complete,
        "dimension_count": len(dimensions),
        "high_importance_coverage": round(high_coverage_ratio, 3),
        "source_routing_ratio": round(routing_ratio, 3),
        "section_traceability_ratio": round(traceability_ratio, 3),
        "section_report_ratio": round(section_report_ratio, 3),
        "budget_within_hard_limits": budget_within_hard_limits,
        "failed_source_leak": failed_source_leak,
        "notes": notes,
    }


def _score_p1_process(summary: dict[str, Any]) -> int:
    stages = set(summary.get("stages") or [])
    required = {"dispatch", "research_plan", "model_analysis", "evidence_merge", "synthesize", "factcheck_revision"}
    if required.issubset(stages):
        return 5
    if {"research_plan", "evidence_merge", "synthesize"}.issubset(stages):
        return 4
    return 2 if stages else 1


def _score_p1_report(report: str) -> int:
    if not report.strip():
        return 1
    fallback_markers = (
        "Model Prior unavailable",
        "deterministic research plan retained",
        "当前可用来源未能完整覆盖",
        "本轮报告综合未能在档位时限内完成",
    )
    if any(marker in report for marker in fallback_markers):
        return 1
    headings = re.findall(r"^##\s+(.+)$", report, flags=re.MULTILINE)
    public_required = ["回答", "参考文献与证据", "置信度附录"]
    if headings == public_required:
        answer = _extract_section_text(report, "回答")
        references = _extract_section_text(report, "参考文献与证据")
        confidence = _extract_section_text(report, "置信度附录")
        internal_leak = bool(re.search(r"\[(?:RAG:|Web:)", answer))
        reference_entries = re.findall(r"(?m)^\d+\.\s+", references)
        complete_entries = references.count("引用内容：")
        confidence_table = "| 关键结论 |" in confidence and "|---|" in confidence
        if (
            answer
            and references
            and confidence
            and not internal_leak
            and confidence_table
            and (not reference_entries or complete_entries == len(reference_entries))
        ):
            return 5
        if answer and references and confidence and not internal_leak:
            return 4
        return 2
    required = ["回答", "研究依据", "可靠性与缺口"]
    hits = sum(item in headings for item in required)
    repeated_reliability = report.count("## 可靠性与缺口") > 1
    sections = {title: _extract_section_text(report, title) for title in required}
    source_blocked = any(title.casefold() in {"rag", "web", "model"} for title in headings)
    reliability_units = [
        line for line in sections["可靠性与缺口"].splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if (
        headings == required
        and all(sections.values())
        and not repeated_reliability
        and not source_blocked
        and len(reliability_units) <= 5
    ):
        return 5
    if hits == 3 and sections["回答"] and not repeated_reliability and not source_blocked:
        return 4
    if hits >= 2:
        return 3
    return 2


def _score_p1_evidence(external_nodes: list[dict], model_nodes: list[dict]) -> int:
    if external_nodes:
        direct_authority = [
            item for item in external_nodes
            if float(item.get("authority_score") or 0.0) >= 0.75
            and (float(item.get("directness") or 0.0) >= 0.6 or item.get("verbatim_quote"))
        ]
        return 5 if len(direct_authority) >= 2 else 4
    if model_nodes:
        return 4
    return 1


def _source_succeeded(item: dict[str, Any], statuses: dict[str, Any]) -> bool:
    source_id = str(item.get("source") or "")
    source = "RAG" if source_id.casefold().endswith("rag") else "Web" if source_id.casefold().endswith("web") else source_id
    payload = statuses.get(source) or statuses.get(source_id)
    if not isinstance(payload, dict):
        return True
    return str(payload.get("status") or "") == "success"


def _importance_value(value: Any) -> float:
    if isinstance(value, str):
        named = {"high": 0.9, "medium": 0.6, "low": 0.3}
        if value.strip().casefold() in named:
            return named[value.strip().casefold()]
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _score_p1_citations(coverage: float, invalid: int, external_nodes: list[dict]) -> int:
    if invalid:
        return 1
    if not external_nodes:
        return 4
    if coverage >= 0.85:
        return 5
    if coverage >= 0.6:
        return 4
    if coverage > 0:
        return 3
    return 1


def _score_p1_verification(status: str, findings: dict[str, Any]) -> int:
    issues = findings.get("issues") or []
    unresolved = [item for item in issues if isinstance(item, dict) and not item.get("resolved")]
    if status == "passed" and not unresolved:
        return 5
    if status == "passed" and not any(item.get("severity") == "high" for item in unresolved):
        return 4
    if status == "needs_review":
        return 2
    return 1


def _extract_section_text(report: str, title: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)",
        report,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _p1_quality_notes(scores: dict[str, int], available_sources: list[str], findings: dict[str, Any]) -> list[str]:
    notes = [f"{name}低于达标线：{score}/5" for name, score in scores.items() if score < 4]
    missing = [source for source in ("RAG", "Web", "Model") if source not in available_sources]
    if missing:
        notes.append(f"本轮未覆盖来源：{', '.join(missing)}。这不会自动判定回答失败。")
    if findings.get("invalid_citation_count"):
        notes.append("存在无法解析到证据项的引用。")
    return notes


def evaluate_run_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Score a run on the Phase 1 + Phase 2 acceptance dimensions."""

    final_answer = str(state.get("final_answer") or "")
    source_statuses = state.get("_source_statuses") or {}
    run_summary = state.get("_run_summary") or {}
    factcheck_status = str(state.get("_factcheck_status") or "")
    deep_research = str(state.get("_deep_research") or "")
    evidence_payload = _load_evidence_payload(str(state.get("_evidence_json") or ""))
    evidence_summary = evidence_payload.get("summary") or {}
    l4_enabled = bool(run_summary.get("l4_enabled", True))

    success_sources = [
        source
        for source, payload in source_statuses.items()
        if payload.get("status") == "success"
    ]
    low_relevance_sources = [
        source
        for source, payload in source_statuses.items()
        if payload.get("status") == "low_relevance"
    ]
    non_evidence_sources = [
        source
        for source, payload in source_statuses.items()
        if payload.get("status") in {"no_evidence", "failed", "fallback"}
    ]
    external_fact_sources = [
        source
        for source in success_sources
        if source_statuses.get(source, {}).get("can_support_external_fact", False)
    ]
    factcheck_findings = state.get("_factcheck_findings") or {}
    claim_coverage = _report_claim_coverage(final_answer)

    scores = {
        "运行过程": _score_run_process(run_summary),
        "报告质量": _score_report_quality(final_answer, claim_coverage),
        "来源可靠性": _score_source_reliability(external_fact_sources, low_relevance_sources, non_evidence_sources),
        "FactCheck有效性": _score_factcheck(factcheck_status, factcheck_findings),
        "证据图结构": _score_evidence_graph(evidence_summary, evidence_payload),
        "L4深化质量": _score_l4(deep_research) if l4_enabled else None,
    }
    active_scores = [score for score in scores.values() if isinstance(score, int)]
    overall = round(sum(active_scores) / len(active_scores), 2)
    model_only = _is_model_only(success_sources, external_fact_sources)
    if model_only:
        overall = min(overall, 3.5)
    # Hard gates: needs_review / only-model / low claim coverage fail outright.
    passed = (
        overall >= 4.0
        and scores["FactCheck有效性"] >= 4
        and scores["证据图结构"] >= 4
        and factcheck_status != "needs_review"
        and not model_only
        and _claim_coverage_ok(evidence_payload, claim_coverage)
    )
    return {
        "scores": scores,
        "overall": overall,
        "passed": passed,
        "success_sources": success_sources,
        "low_relevance_sources": low_relevance_sources,
        "non_evidence_sources": non_evidence_sources,
        "external_fact_sources": external_fact_sources,
        "claim_citation_coverage": claim_coverage,
        "notes": _quality_notes(scores, external_fact_sources, low_relevance_sources, non_evidence_sources),
    }


def _load_evidence_payload(evidence_json: str) -> dict[str, Any]:
    if not evidence_json.strip():
        return {}
    try:
        payload = json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _score_run_process(summary: dict[str, Any]) -> int:
    stages = summary.get("stages") or []
    required = {"dispatch", "evidence_merge", "synthesize", "factcheck"}
    if required.issubset(stages) and summary.get("slo_status") in {"pass", "breached"}:
        return 5
    if {"dispatch", "evidence_merge", "synthesize"}.issubset(stages):
        return 4
    if stages:
        return 3
    return 1


def _score_report_quality(report: str, claim_coverage: dict[str, Any]) -> int:
    """Score structure and traceability instead of template keywords alone."""

    if not report.strip():
        return 1
    required_headings = ["最终结论", "信息来源", "不确定", "证据摘要", "建议"]
    headings = re.findall(r"^#{1,6}\s+(.+)$", report, flags=re.MULTILINE)
    section_hits = sum(1 for term in required_headings if any(term in heading for heading in headings))
    ratio = float(claim_coverage.get("ratio", 0.0))
    chinese_length = len(re.findall(r"[\u4e00-\u9fff]", report))
    target_length = 1200 <= chinese_length <= 2500
    if section_hits >= 5 and ratio >= 0.8 and target_length:
        return 5
    if section_hits >= 4 and ratio >= 0.5:
        return 4
    if section_hits >= 3 and ratio > 0:
        return 3
    return 2


def _score_source_reliability(
    external_fact_sources: list[str],
    low_relevance_sources: list[str],
    non_evidence_sources: list[str],
) -> int:
    """Score based on external-fact-capable sources only (model_inference excluded)."""
    if len(external_fact_sources) >= 2:
        return 5 if not non_evidence_sources else 4
    if len(external_fact_sources) == 1:
        return 4 if low_relevance_sources else 3
    if low_relevance_sources:
        return 2
    return 1


def _score_factcheck(status: str, findings: dict[str, Any]) -> int:
    issues = findings.get("issues") or []
    verified_ratio = float(findings.get("verified_claim_ratio", 0.0))
    if status == "passed" and not issues and verified_ratio >= 0.8:
        return 5
    if status == "passed" and not issues and verified_ratio >= 0.5:
        return 4
    if status == "needs_review":
        return 2
    return 1


def _score_evidence_graph(summary: dict[str, Any], payload: dict[str, Any]) -> int:
    nodes = payload.get("nodes") or []
    statuses = payload.get("source_statuses") or {}
    structured = [
        node for node in nodes
        if node.get("claim")
        and node.get("evidence_class")
        and (node.get("verbatim_quote") or node.get("source") == "Model")
    ]
    if nodes and statuses and "source_counts" in summary and len(structured) / len(nodes) >= 0.8:
        return 5
    if nodes and "source_counts" in summary:
        return 4
    if statuses:
        return 3
    return 1


def _score_l4(deep_research: str) -> int:
    if "证据支持" in deep_research and ("模型推断" in deep_research or "进一步检索" in deep_research):
        return 5
    if deep_research.strip():
        return 4
    return 1


def _quality_notes(
    scores: dict[str, int | None],
    external_fact_sources: list[str],
    low_relevance_sources: list[str],
    non_evidence_sources: list[str],
) -> list[str]:
    notes = []
    for key, score in scores.items():
        if score is not None and score < 4:
            notes.append(f"{key}低于达标线：{score}/5")
    if len(external_fact_sources) + len(low_relevance_sources) < 2:
        notes.append("有效证据来源少于两个，无法证明多源真实共识。")
    if low_relevance_sources:
        notes.append(f"存在弱相关证据来源：{', '.join(low_relevance_sources)}。")
    if non_evidence_sources:
        notes.append(f"存在无证据/失败/降级来源：{', '.join(non_evidence_sources)}。")
    return notes


def _is_model_only(
    success_sources: list[str],
    external_fact_sources: list[str],
) -> bool:
    """Weak contextual hits do not make a Model-only answer externally supported."""
    return "Model" in success_sources and not external_fact_sources


def _claim_coverage_ok(evidence_payload: dict[str, Any], report_coverage: dict[str, Any]) -> bool:
    """Require external evidence and citations for more than half of key claims."""

    nodes = evidence_payload.get("nodes") or []
    if not nodes:
        return False
    external_nodes = [
        node for node in nodes
        if node.get("evidence_class") in EXTERNAL_EVIDENCE_CLASSES
        and node.get("evidence_refs")
        and node.get("verbatim_quote")
    ]
    return bool(external_nodes) and float(report_coverage.get("ratio", 0.0)) > 0.5


def _report_claim_coverage(report: str) -> dict[str, Any]:
    """Estimate citation coverage for conclusion bullets and factual paragraphs."""

    claims = []
    in_conclusion = False
    for raw in report.splitlines():
        line = raw.strip()
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            title = heading.group(1)
            in_conclusion = "最终结论" in title or "核心结论" in title
            continue
        if not line:
            continue
        if re.match(r"^(?:[-*]|\d+[.)])\s+", line) and in_conclusion:
            claims.append(re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line))
    if not claims:
        claims = [
            line.strip()
            for line in report.splitlines()
            if len(line.strip()) >= 30 and not line.lstrip().startswith("#")
        ][:10]
    cited = [
        claim for claim in claims
        if re.search(r"\[(RAG|Web)(?::[^\]]+)?\]", claim)
    ]
    total = len(claims)
    return {
        "total": total,
        "cited": len(cited),
        "ratio": round(len(cited) / total, 3) if total else 0.0,
    }
