"""Markdown and HTML report export."""

from __future__ import annotations

import html
import json
import re
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


def slugify(value: str, max_length: int = 48) -> str:
    normalized = re.sub(r"\s+", "-", value.strip().lower())
    normalized = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", normalized)
    normalized = normalized.strip("-_")
    if not normalized:
        normalized = "research"
    return normalized[:max_length].strip("-_") or "research"


def build_markdown_report(query: str, state: dict[str, Any]) -> str:
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
) -> ReportArtifacts:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{slugify(query)}"
    markdown_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    evidence_json_path = out_dir / f"{stem}.evidence.json"
    deep_evidence_json_path = out_dir / f"{stem}.deep-evidence.json"
    raw_sources_path = out_dir / f"{stem}.sources.md"
    audit_markdown_path = out_dir / f"{stem}.audit.md"

    markdown = build_markdown_report(query, state)
    html_doc = markdown_to_html(markdown)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    evidence_text = str(state.get("_evidence_json") or "").strip()
    if evidence_text:
        try:
            evidence_payload = json.loads(evidence_text)
            evidence_text = json.dumps(evidence_payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        evidence_json_path.write_text(evidence_text + "\n", encoding="utf-8")
    else:
        evidence_json_path = None

    deep_evidence_text = str(state.get("_deep_evidence_json") or "").strip()
    if deep_evidence_text:
        try:
            deep_payload = json.loads(deep_evidence_text)
            deep_evidence_text = json.dumps(deep_payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        deep_evidence_json_path.write_text(deep_evidence_text + "\n", encoding="utf-8")
    else:
        deep_evidence_json_path = None

    raw_sources = _sanitize_report_text(str(state.get("_merged") or "").strip())
    if raw_sources:
        raw_sources_path.write_text(
            f"# 原始来源输出\n\n{raw_sources.rstrip()}\n",
            encoding="utf-8",
        )
    else:
        raw_sources_path = None
    if _is_p1_state(state):
        audit_markdown_path.write_text(build_p1_audit_report(query, state), encoding="utf-8")
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
    return "\n".join(lines)
