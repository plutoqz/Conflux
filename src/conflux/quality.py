"""Deterministic quality checks for a completed Conflux run."""

from __future__ import annotations

import json
import re
from typing import Any

from .source_status import EXTERNAL_EVIDENCE_CLASSES


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
