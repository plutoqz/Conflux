"""Deterministic quality checks for a completed Conflux run."""

from __future__ import annotations

import json
from typing import Any


def evaluate_run_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Score a run on the Phase 1 + Phase 2 acceptance dimensions."""

    final_answer = str(state.get("final_answer") or "")
    source_statuses = state.get("_source_statuses") or {}
    run_summary = state.get("_run_summary") or {}
    factcheck_status = str(state.get("_factcheck_status") or "")
    deep_research = str(state.get("_deep_research") or "")
    evidence_payload = _load_evidence_payload(str(state.get("_evidence_json") or ""))
    evidence_summary = evidence_payload.get("summary") or {}

    success_sources = [
        source
        for source, payload in source_statuses.items()
        if payload.get("status") == "success"
    ]
    failed_or_fallback = [
        source
        for source, payload in source_statuses.items()
        if payload.get("status") in {"failed", "fallback"}
    ]

    scores = {
        "运行过程": _score_run_process(run_summary),
        "报告质量": _score_report_quality(final_answer),
        "来源可靠性": _score_source_reliability(success_sources, failed_or_fallback),
        "FactCheck有效性": _score_factcheck(factcheck_status, state.get("_verified_answer")),
        "证据图结构": _score_evidence_graph(evidence_summary, evidence_payload),
        "L4深化质量": _score_l4(deep_research),
    }
    overall = round(sum(scores.values()) / len(scores), 2)
    passed = overall >= 4.0 and scores["FactCheck有效性"] >= 4 and scores["证据图结构"] >= 4
    return {
        "scores": scores,
        "overall": overall,
        "passed": passed,
        "success_sources": success_sources,
        "failed_or_fallback_sources": failed_or_fallback,
        "notes": _quality_notes(scores, success_sources, failed_or_fallback),
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


def _score_report_quality(report: str) -> int:
    required_terms = ["最终结论", "信息来源", "不确定", "证据", "建议"]
    hits = sum(1 for term in required_terms if term in report)
    if hits >= 5:
        return 5
    if hits >= 4:
        return 4
    if hits >= 3:
        return 3
    return 2 if report.strip() else 1


def _score_source_reliability(success_sources: list[str], failed_or_fallback: list[str]) -> int:
    if len(success_sources) >= 2:
        return 5 if not failed_or_fallback else 4
    if len(success_sources) == 1:
        return 3
    return 1


def _score_factcheck(status: str, verified_answer: Any) -> int:
    text = str(verified_answer or "")
    if status == "passed" and "success 来源" in text:
        return 5
    if status in {"passed", "needs_review"} and "确定性追溯检查" in text:
        return 4
    if status in {"passed", "needs_review"}:
        return 3
    return 1


def _score_evidence_graph(summary: dict[str, Any], payload: dict[str, Any]) -> int:
    nodes = payload.get("nodes") or []
    statuses = payload.get("source_statuses") or {}
    if nodes and statuses and "source_counts" in summary:
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
    return 2


def _quality_notes(scores: dict[str, int], success_sources: list[str], failed_or_fallback: list[str]) -> list[str]:
    notes = []
    for key, score in scores.items():
        if score < 4:
            notes.append(f"{key}低于达标线：{score}/5")
    if len(success_sources) < 2:
        notes.append("有效 success 来源少于两个，无法证明多源真实共识。")
    if failed_or_fallback:
        notes.append(f"存在失败/降级来源：{', '.join(failed_or_fallback)}。")
    return notes
