"""Markdown and HTML report export."""

from __future__ import annotations

import html
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .quality import evaluate_run_quality


REPORT_TITLE = "# Conflux \u8c03\u7814\u62a5\u544a"
FINAL_HEADING = "## \u6700\u7ec8\u62a5\u544a"
SOURCE_STATUS_HEADING = "## \u4fe1\u606f\u6765\u6e90\u72b6\u6001"
FACTCHECK_HEADING = "## FactCheck \u9a8c\u8bc1"
EVIDENCE_HEADING = "## \u8bc1\u636e\u6458\u8981"
EVIDENCE_JSON_HEADING = "## \u9644\u5f55 A\uff1a\u8bc1\u636e\u56fe JSON"
RAW_OUTPUT_HEADING = "## \u9644\u5f55 B\uff1a\u539f\u59cb\u4e09\u6e90\u8f93\u51fa"
RUN_SUMMARY_HEADING = "## \u8fd0\u884c\u6458\u8981"
QUALITY_HEADING = "## \u8d28\u91cf\u8bc4\u5206"


@dataclass(frozen=True)
class ReportArtifacts:
    markdown_path: Path
    html_path: Path
    evidence_json_path: Path | None = None
    raw_sources_path: Path | None = None
    deep_evidence_json_path: Path | None = None
    audit_markdown_path: Path | None = None


def write_staged_markdown_report(
    query: str,
    state: dict[str, Any],
    output_dir: str | Path,
    *,
    run_id: str,
    stage: str,
) -> Path:
    """Persist a draft or verified report without exposing a partial write."""

    normalized = "verified" if stage == "verified" else "draft"
    path = Path(output_dir) / f"{run_id}.{normalized}.md"
    _atomic_write_text(path, build_markdown_report(query, state))
    return path


def promote_staged_markdown_report(staged_path: str | Path, final_path: str | Path) -> Path:
    """Atomically promote the most recent complete staged report."""

    source = Path(staged_path)
    target = Path(final_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve() and source.exists():
        os.replace(source, target)
    return target


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def slugify(value: str, max_length: int = 48) -> str:
    normalized = re.sub(r"\s+", "-", value.strip().lower())
    normalized = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", normalized)
    normalized = normalized.strip("-_")
    if not normalized:
        normalized = "research"
    return normalized[:max_length].strip("-_") or "research"


def build_markdown_report(query: str, state: dict[str, Any]) -> str:
    if _is_v2_state(state):
        return _strip_code_fence(
            str(state.get("_report_markdown") or state.get("final_answer") or "")
        ).rstrip() + "\n"
    if _is_p1_state(state):
        return _build_p1_main_report(query, state)

    final_answer = _sanitize_report_text(_strip_code_fence(str(state.get("final_answer", "")).strip()))
    verified = _sanitize_report_text(str(state.get("_verified_answer", "")).strip())
    deep_research = _sanitize_report_text(str(state.get("_deep_research", "")).strip())
    deep_arbitration = _sanitize_report_text(str(state.get("_deep_arbitration", "")).strip())
    deep_factcheck = _sanitize_report_text(str(state.get("_deep_factcheck_report", "")).strip())
    arbitration = _sanitize_report_text(str(state.get("_arbitration", "")).strip())
    evidence_json = str(state.get("_evidence_json", "")).strip()
    deep_evidence_json = str(state.get("_deep_evidence_json", "")).strip()
    source_statuses = state.get("_source_statuses") or {}
    run_summary = state.get("_run_summary") or {}
    quality_report = state.get("_quality_report") or evaluate_run_quality(state)
    sections = [
        f"{REPORT_TITLE}\n",
        f"- \u67e5\u8be2\uff1a{query}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "- Artifact: Markdown + HTML",
        f"- Run id: {run_summary.get('run_id') or state.get('_run_id') or 'n/a'}",
        f"- Thread id: {run_summary.get('thread_id') or state.get('_thread_id') or 'n/a'}\n",
        FINAL_HEADING,
        _demote_markdown_headings(final_answer or "\u672a\u751f\u6210\u6700\u7ec8\u62a5\u544a\u3002"),
        "",
        SOURCE_STATUS_HEADING,
        _source_status_markdown(source_statuses),
    ]

    sections.extend([
        "",
        FACTCHECK_HEADING,
        _demote_markdown_headings(verified) if verified else "\u672a\u751f\u6210 FactCheck \u7ed3\u679c\u3002",
    ])
    if deep_research:
        sections.extend(["", "## L4 \u6df1\u5316\u7814\u7a76", _demote_markdown_headings(deep_research)])
        if deep_evidence_json:
            sections.extend(["", "## L4 深化证据摘要", _evidence_summary_markdown(deep_evidence_json)])
        if deep_arbitration:
            sections.extend(["", "## L4 深化仲裁", _demote_markdown_headings(deep_arbitration)])
        if deep_factcheck:
            sections.extend(["", "## L4 深化核查", _demote_markdown_headings(deep_factcheck)])
    if arbitration:
        sections.extend(["", "## \u4e09\u6e90\u4ef2\u88c1", _demote_markdown_headings(arbitration)])
    if evidence_json:
        sections.extend(["", EVIDENCE_HEADING, _evidence_summary_markdown(evidence_json)])
        citation_appendix = _rag_citation_appendix(source_statuses)
        if citation_appendix:
            sections.extend(["", "## Appendix C: RAG Chunk Citations", citation_appendix])
        # Evidence JSON and raw outputs are saved as separate appendix files,
        # not included in the main report body to keep it readable.
    if run_summary:
        sections.extend(["", RUN_SUMMARY_HEADING, _run_summary_markdown(run_summary)])
    if quality_report:
        sections.extend(["", QUALITY_HEADING, _quality_report_markdown(quality_report)])
    # Raw source outputs are saved as a separate appendix file.

    return "\n".join(sections).rstrip() + "\n"


def _is_p1_state(state: dict[str, Any]) -> bool:
    summary = state.get("_run_summary") or {}
    return bool(state.get("_research_profile")) or str(summary.get("mode") or "").casefold() == "p1"


def _is_v2_state(state: dict[str, Any]) -> bool:
    summary = state.get("_run_summary") or {}
    return bool(state.get("_report_markdown")) or str(summary.get("mode") or "").casefold() == "answer_first"


def _build_p1_main_report(query: str, state: dict[str, Any]) -> str:
    """Render the user-facing P1 answer without operational audit noise."""

    final_answer = _sanitize_report_text(_strip_code_fence(str(state.get("final_answer") or "").strip()))
    run_summary = state.get("_run_summary") or {}
    sections = [
        REPORT_TITLE,
        "",
        f"- 查询：{query}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Run id: {run_summary.get('run_id') or state.get('_run_id') or 'n/a'}",
        "",
        final_answer or "## 回答\n\n未生成最终报告。\n\n## 研究依据\n\n无。\n\n## 可靠性与缺口\n\n本轮生成失败。",
    ]
    return "\n".join(sections).rstrip() + "\n"


def build_p1_audit_report(query: str, state: dict[str, Any]) -> str:
    """Render P1 planning, evidence, verification, and routing details."""

    source_statuses = state.get("_source_statuses") or {}
    run_summary = state.get("_run_summary") or {}
    quality_report = state.get("_quality_report") or {}
    evidence_json = str(state.get("_evidence_json") or "").strip()
    factcheck = str(state.get("_factcheck_report") or "").strip()
    sections = [
        "# Conflux 研究审计",
        "",
        f"- 查询：{query}",
        f"- Run id: {run_summary.get('run_id') or state.get('_run_id') or 'n/a'}",
        f"- 研究深度：{(state.get('_research_profile') or {}).get('depth', 'unknown')}",
        "",
        "## 模型路由",
        _json_block(state.get("_model_trace") or {}),
        "",
        "## 研究计划",
        _json_block(state.get("_research_plan") or {}),
        "",
        "## 子问题来源覆盖",
        _json_block(state.get("_source_coverage") or []),
        "",
        "## 声明评估",
        _json_block(state.get("_claim_assessments") or []),
        "",
        SOURCE_STATUS_HEADING,
        _source_status_markdown(source_statuses),
        "",
        "## 核验与修订",
        _demote_markdown_headings(factcheck) if factcheck else "未生成核验摘要。",
        _json_block(state.get("_verification_issues") or []),
    ]
    if state.get("_query_archetype") or str(run_summary.get("mode") or "").casefold() in {
        "p15",
        "p1.5",
    }:
        sections.extend([
            "",
            "## P1.5 问题原型与研究策略",
            _json_block({
                "query_archetype": state.get("_query_archetype") or {},
                "research_strategy": state.get("_research_strategy") or {},
            }),
            "",
            "## 动态领域地图",
            _json_block(state.get("_domain_map") or {}),
            "",
            "## 动态运行预算",
            _json_block({
                "allocated": state.get("_research_budget") or {},
                "actual_usage": state.get("_budget_usage") or {},
            }),
            "",
            "## 来源路由",
            _json_block(state.get("_source_plans") or []),
            "",
            "## 维度覆盖矩阵",
            _json_block(state.get("_coverage_matrix") or {}),
            "",
            "## 报告与章节契约",
            _json_block({
                "outline": state.get("_report_outline") or {},
                "sections": state.get("_section_contracts") or [],
                "drafts": state.get("_section_drafts") or [],
                "verification": state.get("_section_verification") or {},
            }),
        ])
    if evidence_json:
        sections.extend(["", EVIDENCE_HEADING, _evidence_summary_markdown(evidence_json)])
    if run_summary:
        sections.extend(["", RUN_SUMMARY_HEADING, _run_summary_markdown(run_summary)])
    if quality_report:
        sections.extend(["", QUALITY_HEADING, _quality_report_markdown(quality_report)])
    return "\n".join(sections).rstrip() + "\n"


def _json_block(value: Any) -> str:
    return "```json\n" + _safe_fenced_json(json.dumps(value, ensure_ascii=False, indent=2)) + "\n```"


def markdown_to_html(markdown: str, title: str = "Conflux \u8c03\u7814\u62a5\u544a") -> str:
    try:
        import markdown as markdown_lib

        body = markdown_lib.markdown(
            markdown,
            extensions=["extra", "tables", "fenced_code", "sane_lists"],
            output_format="html5",
        )
    except Exception:
        body = _fallback_markdown_to_html(markdown)

    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --paper: #ffffff;
      --text: #20242a;
      --muted: #667085;
      --border: #d9dee7;
      --accent: #1b6ef3;
      --code: #f1f4f8;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 40px 20px 64px; }}
    article {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(16, 24, 40, 0.06);
    }}
    h1, h2, h3 {{ line-height: 1.25; margin: 1.6em 0 0.65em; }}
    h1 {{ margin-top: 0; font-size: 2rem; }}
    h2 {{ border-bottom: 1px solid var(--border); padding-bottom: 0.3em; font-size: 1.35rem; }}
    a {{ color: var(--accent); }}
    code, pre {{ background: var(--code); border-radius: 6px; }}
    code {{ padding: 0.1em 0.3em; }}
    pre {{ overflow: auto; padding: 16px; border: 1px solid var(--border); }}
    blockquote {{ border-left: 4px solid var(--border); color: var(--muted); margin-left: 0; padding-left: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
    th, td {{ border: 1px solid var(--border); padding: 8px 10px; vertical-align: top; }}
    th {{ background: #f2f5f9; }}
    @media (max-width: 640px) {{
      article {{ padding: 22px; }}
      main {{ padding: 20px 12px 44px; }}
    }}
  </style>
</head>
<body>
  <main>
    <article>
{body}
    </article>
  </main>
</body>
</html>
"""


def write_report_artifacts(
    query: str,
    state: dict[str, Any],
    output_dir: str | Path = "reports",
    *,
    diagnostic: bool = False,
) -> ReportArtifacts:
    out_dir = Path(output_dir)
    if diagnostic:
        out_dir = out_dir / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{slugify(query)}"
    if diagnostic:
        stem += ".diagnostic"
    markdown_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    evidence_json_path = out_dir / f"{stem}.evidence.json"
    deep_evidence_json_path = out_dir / f"{stem}.deep-evidence.json"
    raw_sources_path = out_dir / f"{stem}.sources.md"
    audit_markdown_path = out_dir / f"{stem}.audit.md"

    artifact_state = state
    if (
        not diagnostic
        and str(state.get("_delivery_status") or "") in {"deliverable", "limited"}
        and str(state.get("_gated_evidence_json") or "").strip()
    ):
        artifact_state = {**state, "_evidence_json": state["_gated_evidence_json"]}
    markdown = build_markdown_report(query, artifact_state)
    if not diagnostic and str(state.get("_delivery_status") or "") == "limited":
        assessment = state.get("_delivery_assessment") or {}
        limitations = ", ".join(str(item) for item in assessment.get("limitations") or [])
        limited_title = "# Conflux 有限证据研究报告"
        markdown = markdown.replace(REPORT_TITLE, limited_title, 1)
        markdown = (
            f"{markdown.splitlines()[0]}\n\n"
            "> 本报告通过基础交付门禁，但存在已披露的非关键证据限制。\n\n"
            f"> 限制项：{limitations or '详见可靠性与缺口部分'}\n\n"
            + "\n".join(markdown.splitlines()[1:]).lstrip()
        )
    elif diagnostic:
        assessment = state.get("_delivery_assessment") or {}
        reasons = ", ".join(str(item) for item in assessment.get("hard_failures") or [])
        diagnostic_title = "# Conflux 研究诊断产物"
        markdown = markdown.replace(REPORT_TITLE, diagnostic_title, 1)
        markdown = (
            f"{markdown.splitlines()[0]}\n\n"
            "> 此运行未通过交付门禁，不应作为正式研究报告使用。\n\n"
            f"> 门禁原因：{reasons or '未满足交付条件'}\n\n"
            + "\n".join(markdown.splitlines()[1:]).lstrip()
        )
    html_doc = markdown_to_html(markdown)
    _atomic_write_text(markdown_path, markdown)
    _atomic_write_text(html_path, html_doc)
    evidence_text = str(artifact_state.get("_evidence_json") or "").strip()
    if evidence_text:
        try:
            evidence_payload = json.loads(evidence_text)
            evidence_text = json.dumps(evidence_payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        _atomic_write_text(evidence_json_path, evidence_text + "\n")
    else:
        evidence_json_path = None

    deep_evidence_text = str(state.get("_deep_evidence_json") or "").strip()
    if deep_evidence_text:
        try:
            deep_payload = json.loads(deep_evidence_text)
            deep_evidence_text = json.dumps(deep_payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        _atomic_write_text(deep_evidence_json_path, deep_evidence_text + "\n")
    else:
        deep_evidence_json_path = None

    raw_sources = _sanitize_report_text(str(state.get("_merged") or "").strip())
    if raw_sources:
        _atomic_write_text(
            raw_sources_path,
            f"# 原始来源输出\n\n{raw_sources.rstrip()}\n",
        )
    else:
        raw_sources_path = None
    if _is_p1_state(state):
        _atomic_write_text(audit_markdown_path, build_p1_audit_report(query, artifact_state))
    else:
        audit_markdown_path = None
    return ReportArtifacts(
        markdown_path=markdown_path,
        html_path=html_path,
        evidence_json_path=evidence_json_path,
        raw_sources_path=raw_sources_path,
        deep_evidence_json_path=deep_evidence_json_path,
        audit_markdown_path=audit_markdown_path,
    )


def write_v2_report_artifacts(
    query: str,
    state: dict[str, Any],
    output_dir: str | Path = "reports",
) -> ReportArtifacts:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{slugify(query)}"
    markdown_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    evidence_json_path = out_dir / f"{stem}.evidence.json"
    raw_sources_path = out_dir / f"{stem}.sources.md"
    audit_markdown_path = out_dir / f"{stem}.audit.md"

    markdown = _strip_code_fence(str(state.get("_report_markdown") or state.get("final_answer") or ""))
    evidence = build_v2_evidence_payload(state)
    raw_sources = (
        "# V2 原始来源输出\n\n"
        "## RAG\n\n" + str(state.get("_rag_results") or "无") + "\n\n"
        "## Web\n\n" + str(state.get("_web_results") or "无") + "\n"
    )
    audit = (
        "# V2 运行审计\n\n"
        "## 确定性指标\n\n" + _json_block(state.get("_audit_metrics") or {}) + "\n\n"
        "## FactCheck\n\n" + _json_block({
            "status": state.get("_factcheck_status") or "",
            "findings": state.get("_factcheck_findings") or {},
            "budget_consumed": state.get("_budget_state") or {},
            "degradation_reason": (state.get("_budget_state") or {}).get("degradation_reasons") or [],
            "dropped_reason": (state.get("_budget_state") or {}).get("dropped_reasons") or [],
        }) + "\n"
    )

    _atomic_write_text(markdown_path, markdown.rstrip() + "\n")
    _atomic_write_text(html_path, markdown_to_html(markdown, title=query))
    _atomic_write_text(evidence_json_path, json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    _atomic_write_text(raw_sources_path, raw_sources)
    _atomic_write_text(audit_markdown_path, audit)
    return ReportArtifacts(
        markdown_path=markdown_path,
        html_path=html_path,
        evidence_json_path=evidence_json_path,
        raw_sources_path=raw_sources_path,
        audit_markdown_path=audit_markdown_path,
    )


def _build_v2_evidence_payload_from_ledger(state: dict[str, Any]) -> dict[str, Any]:
    citation_map = state.get("_citation_map") or {}
    snapshot = state.get("_ledger_snapshot") or {}
    bindings = state.get("_citation_bindings") or {}
    nodes = []
    for record in snapshot.get("records") or []:
        if not isinstance(record, dict) or record.get("visibility", "primary") != "primary":
            continue
        evidence_id = str(record.get("evidence_id") or "")
        nodes.append({
            "id": evidence_id,
            "source": str(record.get("source_type") or ""),
            "claim": str(record.get("claim") or ""),
            "verbatim_quote": str(record.get("verbatim_quote") or ""),
            "evidence_class": str(record.get("evidence_class") or ""),
            "source_identity": str(record.get("source_identity") or ""),
            "evidence_refs": [str(ref) for ref in bindings.get(evidence_id) or []],
            "evidence_ids": [evidence_id],
        })
    for claim in state.get("_claim_records") or []:
        if not isinstance(claim, dict):
            continue
        if claim.get("claim_type") not in {"derived_analysis", "model_analysis"}:
            continue
        attribution = claim.get("generation_attribution") or {}
        nodes.append({
            "id": str(claim.get("claim_id") or f"model-{len(nodes) + 1}"),
            "source": "Model",
            "claim": str(claim.get("text") or ""),
            "evidence_refs": [str(ref) for ref in attribution.get("citation_refs") or []],
            "evidence_ids": [str(value) for value in claim.get("evidence_ids") or []],
            "claim_type": str(claim.get("claim_type") or ""),
        })
    source_counts: dict[str, int] = {}
    for node in nodes:
        source = str(node.get("source") or "")
        source_counts[source] = source_counts.get(source, 0) + 1
    return {
        "schema_version": "v2",
        "summary": {"total_nodes": len(nodes), "source_counts": source_counts},
        "source_statuses": state.get("_source_statuses") or {},
        "nodes": nodes,
        "citation_map": citation_map,
        "audit_metrics": state.get("_audit_metrics") or {},
        "claim_records": state.get("_claim_records") or [],
        "attribution_audit": state.get("_attribution_audit") or {},
        "ledger_snapshot": snapshot,
        "factcheck": {
            "status": state.get("_factcheck_status") or "",
            "findings": state.get("_factcheck_findings") or {},
        },
        "budget_consumed": state.get("_budget_state") or {},
        "degradation_reason": (state.get("_budget_state") or {}).get("degradation_reasons") or [],
        "dropped_reason": (state.get("_budget_state") or {}).get("dropped_reasons") or [],
        "run_summary": state.get("_run_summary") or {},
    }


def build_v2_evidence_payload(state: dict[str, Any]) -> dict[str, Any]:
    if (state.get("_ledger_snapshot") or {}).get("records"):
        return _build_v2_evidence_payload_from_ledger(state)
    citation_map = state.get("_citation_map") or {}
    nodes = []
    for index, (ref, description) in enumerate(citation_map.items(), start=1):
        source = "RAG" if "来源：RAG" in str(description) else "Web"
        claim = str(description).split("（来源：", 1)[0].strip()
        nodes.append({
            "id": f"evidence-{index}",
            "source": source,
            "claim": claim,
            "evidence_refs": [str(ref)],
        })

    for section in state.get("_section_results") or []:
        if section.get("citation_refs"):
            continue
        for claim in section.get("key_claims") or []:
            nodes.append({
                "id": f"model-{len(nodes) + 1}",
                "source": "Model",
                "claim": str(claim),
                "evidence_refs": [],
            })

    if not nodes and str(state.get("_direct_answer") or "").strip():
        nodes.append({
            "id": "model-1",
            "source": "Model",
            "claim": str(state["_direct_answer"])[:500],
            "evidence_refs": [],
        })

    source_counts: dict[str, int] = {}
    for node in nodes:
        source = str(node["source"])
        source_counts[source] = source_counts.get(source, 0) + 1

    return {
        "schema_version": "v2",
        "summary": {
            "total_nodes": len(nodes),
            "source_counts": source_counts,
        },
        "source_statuses": state.get("_source_statuses") or {},
        "nodes": nodes,
        "citation_map": citation_map,
        "audit_metrics": state.get("_audit_metrics") or {},
        "claim_records": state.get("_claim_records") or [],
        "attribution_audit": state.get("_attribution_audit") or {},
        "ledger_snapshot": state.get("_ledger_snapshot") or {},
        "factcheck": {
            "status": state.get("_factcheck_status") or "",
            "findings": state.get("_factcheck_findings") or {},
        },
        "budget_consumed": state.get("_budget_state") or {},
        "degradation_reason": (state.get("_budget_state") or {}).get("degradation_reasons") or [],
        "dropped_reason": (state.get("_budget_state") or {}).get("dropped_reasons") or [],
        "run_summary": state.get("_run_summary") or {},
    }


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    for marker in ("```final", "```markdown", "```"):
        if stripped.startswith(marker):
            stripped = stripped[len(marker):].strip()
            break
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()
    return stripped


def _sanitize_report_text(text: str) -> str:
    """Redact secrets and obvious prompt-injection instructions in reports."""

    if not text:
        return ""
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]", text)
    redacted = re.sub(r"sk-proj-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]", redacted)
    redacted = re.sub(r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]", redacted)
    redacted = re.sub(r"AIza[0-9A-Za-z_-]{35}", "[REDACTED_GOOGLE_KEY]", redacted)
    redacted = re.sub(
        r"(?i)ignore previous instructions[^.\n]*",
        "[REDACTED_PROMPT_INJECTION]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)web source confirmed this\s*:",
        "[REDACTED_PROMPT_INJECTION_CLAIM]:",
        redacted,
    )
    return redacted


def _demote_markdown_headings(text: str, levels: int = 2) -> str:
    def replace(match: re.Match) -> str:
        return "#" * min(6, len(match.group(1)) + levels) + " "

    return re.sub(r"^(#{1,5})\s+", replace, text, flags=re.MULTILINE)


def _safe_fenced_json(text: str) -> str:
    return text.replace("```", "'''")


def _fallback_markdown_to_html(markdown: str) -> str:
    lines = []
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line:
            if in_list:
                lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                lines.append("<ul>")
                in_list = True
            lines.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        lines.append("</ul>")
    return "\n".join(lines)


def _run_summary_markdown(summary: dict[str, Any]) -> str:
    stages = summary.get("stages") or []
    lines = [
        f"- \u6a21\u5f0f\uff1a{summary.get('mode', 'unknown')}",
        f"- Run id: {summary.get('run_id', 'n/a')}",
        f"- Thread id: {summary.get('thread_id', 'n/a')}",
        f"- Checkpoint backend: {summary.get('checkpoint_backend', 'none')}",
        f"- Resumed: {summary.get('resumed', False)}",
        f"- \u8017\u65f6\uff1a{summary.get('elapsed_ms', 0)} ms",
        f"- SLO P95\uff1a{summary.get('slo_p95_ms', 'n/a')} ms",
        f"- SLO \u72b6\u6001\uff1a{summary.get('slo_status', 'unknown')}",
        f"- \u9636\u6bb5\uff1a{', '.join(stages) if stages else 'n/a'}",
    ]
    if "estimated_cost_usd" in summary:
        lines.append(f"- Estimated cost: ${summary.get('estimated_cost_usd')}")
    return "\n".join(lines)


def _source_status_markdown(statuses: dict[str, Any]) -> str:
    if not statuses:
        return "\u65e0\u6765\u6e90\u72b6\u6001\u8bb0\u5f55\u3002"
    lines = [
        "| \u6765\u6e90 | \u72b6\u6001 | \u8be6\u60c5 | \u9519\u8bef/\u8bf4\u660e |",
        "|---|---|---|---|",
    ]
    for source, payload in _iter_source_statuses(statuses):
        status = payload.get("status", "unknown")
        detail = str(payload.get("detail") or "")
        error = str(payload.get("error") or "")
        note = error or str(payload.get("content") or "")[:90].replace("\n", " ")
        lines.append(f"| {_source_label(source)} | {status} | {detail} | {note} |")
    lines.append("")
    lines.append("Rule: `success` sources support factual evidence; `low_relevance` sources are weak contextual evidence; `no_evidence` / `failed` / `fallback` sources are excluded.")
    return "\n".join(lines)


def _evidence_summary_markdown(evidence_json: str) -> str:
    try:
        payload = json.loads(evidence_json)
    except json.JSONDecodeError:
        return "\u8bc1\u636e\u56fe JSON \u65e0\u6cd5\u89e3\u6790\u3002"

    summary = payload.get("summary") or {}
    statuses = payload.get("source_statuses") or {}
    lines = [
        f"- \u8bc1\u636e\u8282\u70b9\u603b\u6570\uff1a{summary.get('total_nodes', 0)}",
        f"- True multi-source consensus clusters: {summary.get('true_consensus_count', summary.get('consensus_count', 0))}",
        f"- Uncontested nodes: {summary.get('uncontested_count', 0)}",
        f"- Contested nodes: {summary.get('contested_count', 0)}",
        f"- Single-source nodes: {summary.get('single_source_count', 0)}",
        f"- Average authority: {summary.get('avg_authority', 0)}",
    ]
    if statuses:
        weak = [
            source
            for source, item in statuses.items()
            if item.get("status") == "low_relevance"
        ]
        excluded = [
            source
            for source, item in statuses.items()
            if item.get("status") in {"no_evidence", "failed", "fallback"}
        ]
        lines.append(f"- Weak evidence sources: {', '.join(weak) if weak else 'none'}")
        lines.append(f"- Excluded sources: {', '.join(excluded) if excluded else 'none'}")
    pairs = summary.get("contested_pairs") or []
    if pairs:
        lines.append("- Conflict summary: " + "; ".join(f"{item.get('a')} vs {item.get('b')}" for item in pairs[:3]))
    return "\n".join(lines)


def _rag_citation_appendix(statuses: dict[str, Any]) -> str:
    rag_payload = statuses.get("builtin.rag") or statuses.get("RAG") or {}
    citations = (rag_payload.get("metadata") or {}).get("citations") or []
    if not citations:
        return ""
    lines = [
        "| Ref | Source | Chunk | Parent | Char Range | Excerpt |",
        "|---|---|---|---|---|---|",
    ]
    for item in citations:
        ref = str(item.get("ref") or "")
        source = str(item.get("source") or "")
        chunk_id = str(item.get("chunk_id") or "")
        parent_id = str(item.get("parent_id") or "")
        start = item.get("char_start")
        end = item.get("char_end")
        range_text = f"{start}-{end}" if start is not None and end is not None else "n/a"
        excerpt = str(item.get("text") or "").replace("|", "\\|").replace("\n", " ")[:220]
        lines.append(f"| {ref} | {source} | {chunk_id} | {parent_id} | {range_text} | {excerpt} |")
    return "\n".join(lines)


def _iter_source_statuses(statuses: dict[str, Any]):
    """Prefer namespaced statuses and skip their legacy aliases in reports."""

    aliases = {"RAG": "builtin.rag", "Web": "builtin.web", "Model": "builtin.model"}
    seen: set[str] = set()
    preferred = [key for key in ("builtin.rag", "builtin.web", "builtin.model") if key in statuses]
    preferred.extend(
        legacy for legacy, namespaced in aliases.items()
        if namespaced not in statuses and legacy in statuses
    )
    preferred.extend(
        key for key in statuses if key not in preferred and key not in aliases
    )
    for source in preferred:
        if source in seen:
            continue
        seen.add(source)
        yield source, statuses.get(source) or {}


def _source_label(source: str) -> str:
    return {
        "builtin.rag": "RAG",
        "builtin.web": "Web",
        "builtin.model": "Model",
    }.get(source, source)


def _quality_report_markdown(report: dict[str, Any]) -> str:
    scores = report.get("scores") or {}
    lines = [
        f"- \u603b\u5206\uff1a{report.get('overall', 0)} / 5",
        "- \u662f\u5426\u8fbe\u6807\uff1a\u662f" if report.get("passed") else "- \u662f\u5426\u8fbe\u6807\uff1a\u5426",
    ]
    for name, score in scores.items():
        lines.append(f"- {name}\uff1a{score} / 5" if score is not None else f"- {name}：不适用")
    notes = report.get("notes") or []
    if notes:
        lines.append("- \u5907\u6ce8\uff1a" + "\uff1b".join(str(note) for note in notes))
    generalization = report.get("generalization") or {}
    if isinstance(generalization, dict) and generalization:
        lines.extend([
            f"- P1.5 泛化总分：{generalization.get('overall', 0)} / 5",
            "- P1.5 泛化达标：是" if generalization.get("passed") else "- P1.5 泛化达标：否",
            f"- 高重要性维度覆盖：{generalization.get('high_importance_coverage', 0):.0%}",
            f"- 章节追溯率：{generalization.get('section_traceability_ratio', 0):.0%}",
        ])
    return "\n".join(lines)
