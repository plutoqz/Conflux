"""Markdown and JSON persistence for progress snapshots and audits."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import ProgressAuditReport, ProjectSnapshot


@dataclass(slots=True)
class ProgressArtifacts:
    markdown_path: Path
    json_path: Path
    snapshot_path: Path


def load_snapshot(path: str | Path) -> ProjectSnapshot | None:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return None
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return ProjectSnapshot.from_dict(payload)


def write_snapshot(snapshot: ProjectSnapshot, path: str | Path) -> Path:
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snapshot_path


def build_progress_markdown(report: ProgressAuditReport) -> str:
    snapshot = report.snapshot
    lines = [
        f"# 项目进度审计：{report.project_id}",
        "",
        "## 审计摘要",
        f"- 周期：{report.period}",
        f"- 基线状态：`{report.baseline_status}`",
        f"- 真实进展：{len(report.real_progress)}",
        f"- 风险：{len(report.risks)}",
        "",
        "## 真实进展",
        "",
    ]
    if report.real_progress:
        for claim in report.real_progress:
            lines.append(f"- {claim.summary}")
            lines.extend(f"  - 证据：`{ref}`" for ref in claim.evidence_refs)
    else:
        lines.append("- 本周期尚无可验证的真实进展。")
    lines.extend(_text_section("弱信号", report.weak_signals, "未检测到弱信号。"))
    lines.extend(_text_section("风险", report.risks, "当前未检测到风险。"))
    lines.extend(_text_section("建议下一步", report.recommended_next_actions, "暂无建议。"))
    if snapshot:
        git_summary = (
            f"`{snapshot.git_branch or 'detached'}` @ `{snapshot.git_head[:12] or 'unknown'}`"
            if snapshot.git_available
            else "不适用（非 Git 研究目录）"
        )
        lines.extend([
            "",
            "## 当前快照",
            f"- 路径：`{snapshot.path}`",
            f"- Git：{git_summary}",
            f"- 未提交文件：{len(snapshot.dirty_files)}",
            f"- 测试状态：`{snapshot.test_result.status}`",
            f"- 研究产物：{len(snapshot.result_files)}",
            f"- 报告文件：{len(snapshot.report_files)}",
        ])
    return "\n".join(lines).rstrip() + "\n"


def write_progress_artifacts(
    report: ProgressAuditReport,
    *,
    out_dir: str | Path,
) -> ProgressArtifacts:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / "progress_audit.md"
    json_path = root / "progress_audit.json"
    snapshot_path = root / "project_snapshot.json"
    markdown_path.write_text(build_progress_markdown(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if report.snapshot:
        write_snapshot(report.snapshot, snapshot_path)
    return ProgressArtifacts(markdown_path, json_path, snapshot_path)


def _text_section(title: str, values: list[str], empty: str) -> list[str]:
    lines = ["", f"## {title}", ""]
    lines.extend(f"- {value}" for value in values)
    if not values:
        lines.append(f"- {empty}")
    return lines
