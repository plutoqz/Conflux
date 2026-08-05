"""Acceptance checks for real Conflux report artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = [
    "## 最终报告",
    "## 信息来源状态",
    "## FactCheck 验证",
    "## 证据摘要",
    "## 运行摘要",
    "## 质量评分",
]

REQUIRED_FINAL_TERMS = ["最终结论", "信息来源", "不确定", "证据"]
VALID_STATUSES = {"success", "low_relevance", "no_evidence", "failed", "fallback"}
EVIDENCE_STATUSES = {"success", "low_relevance"}
NON_EVIDENCE_STATUSES = {"no_evidence", "failed", "fallback"}


@dataclass
class AcceptanceResult:
    """Machine-readable acceptance result for one md/html report pair."""

    markdown_path: str
    html_path: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    evidence_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "markdown_path": self.markdown_path,
            "html_path": self.html_path,
            "passed": self.passed,
            "checks": self.checks,
            "issues": self.issues,
            "evidence_summary": self.evidence_summary,
        }


def validate_report_pair(markdown_path: str | Path, html_path: str | Path) -> AcceptanceResult:
    """Validate report artifacts against the Phase 1 + Phase 2 completion gates."""

    md_path = Path(markdown_path)
    html_doc_path = Path(html_path)
    issues: list[str] = []
    checks: dict[str, bool] = {}
    evidence_summary: dict[str, Any] = {}

    markdown = _read_text(md_path, issues, "Markdown")
    html = _read_text(html_doc_path, issues, "HTML")

    checks["markdown_exists"] = md_path.exists() and bool(markdown)
    checks["html_exists"] = html_doc_path.exists() and bool(html)
    checks["html_document"] = "<!doctype html>" in html.lower() and "<html" in html.lower()
    if not checks["html_document"]:
        issues.append("HTML 报告不是完整 HTML 文档。")

    evidence_payload = _extract_evidence_payload(markdown, issues, md_path)
    if evidence_payload.get("schema_version") == "v2":
        return _validate_v2_report(
            md_path,
            html_doc_path,
            markdown,
            evidence_payload,
            checks,
            issues,
        )

    for section in REQUIRED_SECTIONS:
        key = f"section:{section}"
        checks[key] = section in markdown
        if not checks[key]:
            issues.append(f"Markdown 缺少必需小节：{section}")

    final_report = _extract_section(markdown, "## 最终报告")
    checks["final_report_terms"] = all(term in final_report for term in REQUIRED_FINAL_TERMS)
    if not checks["final_report_terms"]:
        issues.append("最终报告缺少最终结论/信息来源/不确定性/证据等关键内容。")

    source_statuses = _parse_source_status_table(markdown)
    checks["source_statuses_present"] = set(source_statuses) >= {"RAG", "Web", "Model"}
    if not checks["source_statuses_present"]:
        issues.append("信息来源状态表没有覆盖 RAG/Web/Model。")
    checks["source_status_values_valid"] = all(
        payload.get("status") in VALID_STATUSES for payload in source_statuses.values()
    )
    if not checks["source_status_values_valid"]:
        issues.append("来源状态必须是 success / low_relevance / no_evidence / failed / fallback。")

    nodes = evidence_payload.get("nodes") or []
    graph_statuses = evidence_payload.get("source_statuses") or {}
    graph_summary = evidence_payload.get("summary") or {}
    evidence_summary = {
        "total_nodes": graph_summary.get("total_nodes", 0),
        "source_counts": graph_summary.get("source_counts", {}),
        "source_statuses": {
            source: payload.get("status") for source, payload in graph_statuses.items()
        },
    }
    checks["evidence_payload_parseable"] = bool(evidence_payload)
    checks["evidence_has_source_statuses"] = set(graph_statuses) >= {"RAG", "Web", "Model"}
    checks["evidence_has_nodes"] = bool(nodes) and all(
        str(node.get("claim") or "").strip() for node in nodes
    )
    if not checks["evidence_payload_parseable"]:
        issues.append("证据图 JSON 缺失或无法解析。")
    if not checks["evidence_has_source_statuses"]:
        issues.append("证据图缺少三源状态。")
    if not checks["evidence_has_nodes"]:
        issues.append("证据图没有有效声明节点。")

    non_evidence_sources = {
        source
        for source, payload in graph_statuses.items()
        if payload.get("status") in NON_EVIDENCE_STATUSES
    }
    invalid_nodes = [
        node for node in nodes if node.get("source") in non_evidence_sources
    ]
    checks["non_evidence_sources_excluded_from_nodes"] = not invalid_nodes
    if invalid_nodes:
        issues.append("no_evidence/failed/fallback 来源出现在证据节点中，说明它参与了证据投票。")

    rag_success = graph_statuses.get("RAG", {}).get("status") in EVIDENCE_STATUSES
    rag_nodes = [node for node in nodes if node.get("source") == "RAG"]
    rag_citation_pattern = r"\[RAG:[^\]\s]+#chunk-[^\]\s]+\]"
    checks["rag_chunk_citations"] = (
        not rag_success
        or not rag_nodes
        or bool(re.search(rag_citation_pattern, markdown))
        or any("evidence_refs" not in node for node in rag_nodes)
        or all(node.get("evidence_refs") for node in rag_nodes)
    )
    if not checks["rag_chunk_citations"]:
        issues.append("RAG success source is missing chunk-level citations such as [RAG:file#chunk-001].")

    factcheck = _extract_section(markdown, "## FactCheck 验证")
    checks["factcheck_traceability"] = (
        "确定性追溯检查" in factcheck
        and "success 来源" in factcheck
        and ("low_relevance 来源" in factcheck or "证据节点数" in factcheck)
    )
    if not checks["factcheck_traceability"]:
        issues.append("FactCheck 缺少确定性追溯检查或 success/low_relevance 来源摘要。")

    checks["quality_passed_flag"] = "是否达标：是" in markdown
    if not checks["quality_passed_flag"]:
        issues.append("质量评分未给出达标结论，或当前结论未达标。")

    passed = all(checks.values())
    return AcceptanceResult(
        markdown_path=str(md_path),
        html_path=str(html_doc_path),
        passed=passed,
        checks=checks,
        issues=issues,
        evidence_summary=evidence_summary,
    )


def _validate_v2_report(
    markdown_path: Path,
    html_path: Path,
    markdown: str,
    evidence_payload: dict[str, Any],
    checks: dict[str, bool],
    issues: list[str],
) -> AcceptanceResult:
    graph_statuses = evidence_payload.get("source_statuses") or {}
    nodes = evidence_payload.get("nodes") or []
    graph_summary = evidence_payload.get("summary") or {}
    citation_map = evidence_payload.get("citation_map") or {}
    audit_metrics = evidence_payload.get("audit_metrics") or {}
    factcheck = evidence_payload.get("factcheck") or {}
    run_summary = evidence_payload.get("run_summary") or {}
    ledger_snapshot = evidence_payload.get("ledger_snapshot") or run_summary.get("ledger_snapshot") or {}
    claim_records = evidence_payload.get("claim_records") or run_summary.get("claim_records") or []
    attribution_audit = evidence_payload.get("attribution_audit") or run_summary.get("attribution_audit") or {}

    required_sections = ("## 直接回答", "## 可信度说明", "## FactCheck 验证")
    checks["v2_required_sections"] = all(section in markdown for section in required_sections)
    if not checks["v2_required_sections"]:
        issues.append("V2 报告缺少直接回答、可信度说明或 FactCheck 验证小节。")

    checks["source_statuses_present"] = set(graph_statuses) >= {"RAG", "Web", "Model"}
    checks["source_status_values_valid"] = all(
        payload.get("status") in VALID_STATUSES for payload in graph_statuses.values()
    )
    if not checks["source_statuses_present"]:
        issues.append("V2 证据附件没有覆盖 RAG/Web/Model 来源状态。")
    if not checks["source_status_values_valid"]:
        issues.append("V2 来源状态值无效。")

    checks["evidence_has_nodes"] = bool(nodes) and all(
        str(node.get("claim") or "").strip() for node in nodes
    )
    if not checks["evidence_has_nodes"]:
        issues.append("V2 证据附件没有有效声明节点。")

    non_evidence_sources = {
        source for source, payload in graph_statuses.items()
        if payload.get("status") in NON_EVIDENCE_STATUSES
    }
    invalid_nodes = [node for node in nodes if node.get("source") in non_evidence_sources]
    checks["non_evidence_sources_excluded_from_nodes"] = not invalid_nodes
    if invalid_nodes:
        issues.append("V2 非证据来源出现在证据节点中。")

    external_refs = [
        str(ref)
        for node in nodes
        if node.get("source") in {"RAG", "Web"}
        for ref in node.get("evidence_refs") or []
    ]
    checks["citations_resolve"] = (
        int(audit_metrics.get("invalid_citation_refs") or 0) == 0
        and all(ref in citation_map for ref in external_refs)
    )
    if not checks["citations_resolve"]:
        issues.append("V2 报告存在无法解析的引用。")

    checks["report_available"] = bool(run_summary.get("report_available"))
    if not checks["report_available"]:
        issues.append("V2 运行摘要未确认正式报告可用。")

    checks["factcheck_structured"] = (
        factcheck.get("status") in {"passed", "partial", "skipped"}
        and isinstance(factcheck.get("findings"), dict)
    )
    if not checks["factcheck_structured"]:
        issues.append("V2 FactCheck 未完成结构化记录或验证失败。")

    protocol_present = bool(ledger_snapshot.get("snapshot_id") or claim_records)
    checks["ledger_snapshot_present"] = (
        not protocol_present
        or bool(ledger_snapshot.get("snapshot_id"))
    )
    checks["claim_records_structured"] = (
        not protocol_present
        or all(
            isinstance(item, dict)
            and str(item.get("claim_id") or "").strip()
            and str(item.get("text") or "").strip()
            and isinstance(item.get("derivation_inputs") or [], list)
            and isinstance(item.get("verification_result") or {}, dict)
            for item in claim_records
        )
    )
    delivery_status = str(run_summary.get("delivery_status") or "")
    checks["delivery_decision_present"] = (
        not protocol_present
        or delivery_status in {"deliverable", "limited", "diagnostic_only"}
    )
    generation_trace_invalid = bool(
        audit_metrics.get("generation_trace_invalid")
        or attribution_audit.get("generation_trace_invalid")
    )
    checks["attribution_audit_consistent"] = (
        not protocol_present
        or not generation_trace_invalid
        or delivery_status == "diagnostic_only"
    )
    if not checks["ledger_snapshot_present"]:
        issues.append("V2 EvidenceLedger 快照缺少不可变 snapshot_id。")
    if not checks["claim_records_structured"]:
        issues.append("V2 ClaimRecord 缺少声明文本或验证结构。")
    if not checks["delivery_decision_present"]:
        issues.append("V2 运行摘要缺少最终交付决策。")
    if not checks["attribution_audit_consistent"]:
        issues.append("V2 归因审计失败但最终交付决策未降级为 diagnostic_only。")

    evidence_summary = {
        "total_nodes": graph_summary.get("total_nodes", 0),
        "source_counts": graph_summary.get("source_counts", {}),
        "source_statuses": {
            source: payload.get("status") for source, payload in graph_statuses.items()
        },
    }
    return AcceptanceResult(
        markdown_path=str(markdown_path),
        html_path=str(html_path),
        passed=all(checks.values()),
        checks=checks,
        issues=issues,
        evidence_summary=evidence_summary,
    )


def _read_text(path: Path, issues: list[str], label: str) -> str:
    if not path.exists():
        issues.append(f"{label} 文件不存在：{path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(f"{label} 文件不是 UTF-8 编码：{path}")
        return ""


def _extract_section(markdown: str, heading: str) -> str:
    start = markdown.find(heading)
    if start < 0:
        return ""
    rest = markdown[start + len(heading):]
    next_heading = re.search(r"\n##\s+", rest)
    if next_heading:
        rest = rest[: next_heading.start()]
    return rest.strip()


def _parse_source_status_table(markdown: str) -> dict[str, dict[str, str]]:
    section = _extract_section(markdown, "## 信息来源状态")
    statuses: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        source, status = cells[0], cells[1]
        if source == "来源":
            continue
        if source in {"RAG", "Web", "Model"}:
            statuses[source] = {"status": status}
    return statuses


def _extract_evidence_payload(
    markdown: str,
    issues: list[str],
    markdown_path: Path | None = None,
) -> dict[str, Any]:
    appendix = _extract_section(markdown, "## 附录 A：证据图 JSON")
    if not appendix:
        if markdown_path is None:
            return {}
        sidecar = markdown_path.with_suffix(".evidence.json")
        if not sidecar.exists():
            issues.append(f"证据图附件不存在：{sidecar}")
            return {}
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            issues.append(f"证据图附件无法解析：{exc}")
            return {}
        return payload if isinstance(payload, dict) else {}
    matches = re.findall(r"```json\s*(.*?)```", appendix, flags=re.DOTALL)
    if not matches:
        return {}
    try:
        payload = json.loads(matches[0].strip())
    except json.JSONDecodeError as exc:
        issues.append(f"证据图 JSON 解析失败：{exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Conflux Markdown/HTML report artifacts.")
    parser.add_argument("markdown_path", help="Markdown report path")
    parser.add_argument("html_path", help="HTML report path")
    args = parser.parse_args(argv)

    result = validate_report_pair(args.markdown_path, args.html_path)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
