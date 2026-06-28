"""报告导出：生成 Markdown 与 HTML 两种交付物。"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .quality import evaluate_run_quality


@dataclass(frozen=True)
class ReportArtifacts:
    """一次调研的文件交付物。"""

    markdown_path: Path
    html_path: Path


def slugify(value: str, max_length: int = 48) -> str:
    """将查询文本转换为适合文件名的短 slug。"""
    normalized = re.sub(r"\s+", "-", value.strip().lower())
    normalized = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", normalized)
    normalized = normalized.strip("-_")
    if not normalized:
        normalized = "research"
    return normalized[:max_length].strip("-_") or "research"


def build_markdown_report(query: str, state: dict[str, Any]) -> str:
    """把多智能体状态整理成可编辑的 Markdown 报告。"""
    final_answer = _strip_code_fence(str(state.get("final_answer", "")).strip())
    verified = str(state.get("_verified_answer", "")).strip()
    deep_research = str(state.get("_deep_research", "")).strip()
    arbitration = str(state.get("_arbitration", "")).strip()
    evidence_json = str(state.get("_evidence_json", "")).strip()
    source_statuses = state.get("_source_statuses") or {}
    run_summary = state.get("_run_summary") or {}
    quality_report = state.get("_quality_report") or evaluate_run_quality(state)
    merged = str(state.get("_merged", "")).strip()

    sections = [
        f"# Conflux 调研报告\n",
        f"- 查询：{query}",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 交付物：Markdown + HTML\n",
        "## 最终报告\n",
        _demote_markdown_headings(final_answer or "未生成最终报告。"),
        "\n## 信息来源状态\n",
        _source_status_markdown(source_statuses),
    ]

    if verified:
        sections.extend(["\n## FactCheck 验证\n", _demote_markdown_headings(verified)])
    else:
        sections.extend(["\n## FactCheck 验证\n", "未生成 FactCheck 结果。"])
    if deep_research:
        sections.extend(["\n## L4 深化研究\n", _demote_markdown_headings(deep_research)])
    if arbitration:
        sections.extend(["\n## 三源仲裁\n", _demote_markdown_headings(arbitration)])
    if evidence_json:
        sections.extend(["\n## 证据摘要\n", _evidence_summary_markdown(evidence_json)])
        sections.extend(["\n## 附录 A：证据图 JSON\n", f"```json\n{_safe_fenced_json(evidence_json)}\n```"])
    if run_summary:
        sections.extend(["\n## 运行摘要\n", _run_summary_markdown(run_summary)])
    if quality_report:
        sections.extend(["\n## 质量评分\n", _quality_report_markdown(quality_report)])
    if merged:
        sections.extend(["\n## 附录 B：原始三源输出\n", _demote_markdown_headings(merged)])

    return "\n".join(sections).rstrip() + "\n"


def markdown_to_html(markdown: str, title: str = "Conflux 调研报告") -> str:
    """将 Markdown 转为自包含 HTML。"""
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
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 64px;
    }}
    article {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(16, 24, 40, 0.06);
    }}
    h1, h2, h3 {{
      line-height: 1.25;
      margin: 1.6em 0 0.65em;
    }}
    h1 {{
      margin-top: 0;
      font-size: 2rem;
    }}
    h2 {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.3em;
      font-size: 1.35rem;
    }}
    a {{ color: var(--accent); }}
    code, pre {{
      background: var(--code);
      border-radius: 6px;
    }}
    code {{ padding: 0.1em 0.3em; }}
    pre {{
      overflow: auto;
      padding: 16px;
      border: 1px solid var(--border);
    }}
    blockquote {{
      border-left: 4px solid var(--border);
      color: var(--muted);
      margin-left: 0;
      padding-left: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 8px 10px;
      vertical-align: top;
    }}
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
    """写入 Markdown 和 HTML 报告文件。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{slugify(query)}"
    markdown_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"

    markdown = build_markdown_report(query, state)
    html_doc = markdown_to_html(markdown)

    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")

    return ReportArtifacts(markdown_path=markdown_path, html_path=html_path)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```final"):
        stripped = stripped[len("```final") :].strip()
    if stripped.startswith("```markdown"):
        stripped = stripped[len("```markdown") :].strip()
    if stripped.startswith("```"):
        stripped = stripped[3:].strip()
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()
    return stripped


def _demote_markdown_headings(text: str, levels: int = 2) -> str:
    """Keep embedded model Markdown from breaking report-level sections."""

    def replace(match: re.Match) -> str:
        hashes = match.group(1)
        return "#" * min(6, len(hashes) + levels) + " "

    return re.sub(r"^(#{1,5})\s+", replace, text, flags=re.MULTILINE)


def _safe_fenced_json(text: str) -> str:
    """Prevent nested model fences inside JSON strings from closing the JSON fence."""

    return text.replace("```", "'''")


def _fallback_markdown_to_html(markdown: str) -> str:
    """极简 Markdown fallback，避免可选依赖缺失时无法导出 HTML。"""
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
        f"- 模式：{summary.get('mode', 'unknown')}",
        f"- 耗时：{summary.get('elapsed_ms', 0)} ms",
        f"- SLO P95：{summary.get('slo_p95_ms', 'n/a')} ms",
        f"- SLO 状态：{summary.get('slo_status', 'unknown')}",
        f"- 阶段：{', '.join(stages) if stages else 'n/a'}",
    ]
    return "\n".join(lines)


def _source_status_markdown(statuses: dict[str, Any]) -> str:
    if not statuses:
        return "无来源状态记录。"
    lines = [
        "| 来源 | 状态 | 详情 | 错误/说明 |",
        "|---|---|---|---|",
    ]
    for source in ("RAG", "Web", "Model"):
        payload = statuses.get(source) or {}
        status = payload.get("status", "unknown")
        detail = str(payload.get("detail") or "")
        error = str(payload.get("error") or "")
        note = error or str(payload.get("content") or "")[:90].replace("\n", " ")
        lines.append(f"| {source} | {status} | {detail} | {note} |")
    lines.append("")
    lines.append("说明：只有 `success` 来源可参与共识投票；`failed` / `fallback` 不作为事实证据。")
    return "\n".join(lines)


def _evidence_summary_markdown(evidence_json: str) -> str:
    try:
        payload = json.loads(evidence_json)
    except json.JSONDecodeError:
        return "证据图 JSON 无法解析。"

    summary = payload.get("summary") or {}
    statuses = payload.get("source_statuses") or {}
    lines = [
        f"- 证据节点总数：{summary.get('total_nodes', 0)}",
        f"- 共识/未冲突节点：{summary.get('consensus_count', 0)}",
        f"- 冲突节点：{summary.get('contested_count', 0)}",
        f"- 单源节点：{summary.get('single_source_count', 0)}",
        f"- 平均来源权威分：{summary.get('avg_authority', 0)}",
    ]
    if statuses:
        failed = [
            source
            for source, item in statuses.items()
            if item.get("status") in {"failed", "fallback"}
        ]
        lines.append(f"- 失败/降级来源：{', '.join(failed) if failed else '无'}")
    pairs = summary.get("contested_pairs") or []
    if pairs:
        lines.append("- 冲突摘要：" + "；".join(f"{p.get('a')} vs {p.get('b')}" for p in pairs[:3]))
    return "\n".join(lines)


def _quality_report_markdown(report: dict[str, Any]) -> str:
    scores = report.get("scores") or {}
    lines = [
        f"- 总分：{report.get('overall', 0)} / 5",
        f"- 是否达标：{'是' if report.get('passed') else '否'}",
    ]
    for name, score in scores.items():
        lines.append(f"- {name}：{score} / 5")
    notes = report.get("notes") or []
    if notes:
        lines.append("- 备注：" + "；".join(str(note) for note in notes))
    return "\n".join(lines)
