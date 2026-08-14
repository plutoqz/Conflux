"""P4.3 D 导师周报草稿 — 确定性数据注入 + LLM 仅组织语言 + 事后校验（D2–D4）。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from .memory import recall_for_query
from .projects.cycle_audit import (
    build_cycle_audit,
    latest_confirmed_summary,
)

_REPORT_SYSTEM = (
    "你是研究项目周报撰写助手。你只能整理给定的数据：不得编造任何数字、"
    "提交哈希、实验、论文或结论。用中文输出 Markdown。"
)

_REPORT_USER_TEMPLATE = """为研究生项目撰写一份导师周报草稿。

背景（上一周期已确认摘要，仅供上下文，不要重复数字）：
{previous_summary}

本周期确定性数据（只允许引用这些数据；不要引入任何外部知识）：
{blocks}

个人风格偏好（仅作参考）：{style_hint}

写作要求：
1. 逐条列出「本周期进展」，每条必须含证据括号（如 <exp:xxx>、<git:abc>、<run:yyy>）。
2. 明确列出「风险与失败」，只写 blocks 中失败数据对应的条目。
3. 「下一步建议」严格来自 blocks 中的 next_cycle_candidates。
4. 结尾附「数据清单」小节，原样列出 blocks 中所有数字与哈希。
5. 数据未覆盖的内容标记为「（暂缺）」。
"""

_MAX_SOURCE_CHARS = 600


def _memory_style_banner_uncached() -> str:
    try:
        return recall_for_query("周报 风格 偏好", max_entries=2)
    except Exception:
        return ""


style_hint_cache: dict[str, str] = {}


def _memory_style_banner() -> str:
    key = "banner"
    if key in style_hint_cache:
        return style_hint_cache[key]
    banner = _memory_style_banner_uncached()
    style_hint_cache[key] = banner
    return banner


def _utc_iso() -> str:
    from datetime import datetime, timezone

    try:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return str(int(time.time()))


def _experiment_blocks(experiments: list[dict[str, Any]]) -> str:
    lines = ["实验记录（数字/哈希来自 experiments 表）："]
    for item in experiments[:20]:
        metrics = item.get("metrics") or {}
        metric_text = "、".join(f"{key}={value}" for key, value in sorted(metrics.items())[:5])
        line = f"- [{item.get('status')}] {item.get('name')} <exp:{item.get('id')}>"
        if metric_text:
            line += f" 指标 {metric_text}"
        if item.get("commit_hash"):
            line += f" 提交 {item.get('commit_hash')}"
        if item.get("hypothesis"):
            line += f" 假设：{str(item.get('hypothesis'))[:120]}"
        lines.append(line)
    return "\n".join(lines)


def _assemble_blocks(audit: dict[str, Any], experiments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    claims = audit.get("real_progress") or []
    if claims:
        lines = ["本周期真实进展（证据链接）："]
        for claim in claims[:25]:
            refs = " ".join(f"`{ref}`" for ref in (claim.get("evidence_refs") or [])[:5])
            criteria = " ".join(f"验收标准：{c}" for c in (claim.get("acceptance_criteria") or [])[:3])
            lines.append(f"- {claim.get('summary')}  {refs} {criteria}")
        blocks.append("\n".join(lines))
    if experiments:
        blocks.append(_experiment_blocks(experiments))
    risks = audit.get("risks") or []
    failed = audit.get("failed_experiments") or []
    if risks or failed:
        lines = ["风险与失败（仅来自审计/实验数据）："]
        lines.extend(f"- (风险) {item}" for item in risks[:12])
        lines.extend(f"- (失败) {item.get('summary')}" for item in failed[:12])
        blocks.append("\n".join(lines))
    candidates = audit.get("next_cycle_candidates") or []
    if candidates:
        lines = ["下一周期建议候选："]
        lines.extend(f"- {item.get('summary')}" for item in candidates[:10])
        blocks.append("\n".join(lines))
    if not blocks:
        blocks.append("（本周期无新增确定性数据。）")
    return "\n\n".join(blocks)


def _prompt_for(
    audit: dict[str, Any],
    experiments: list[dict[str, Any]],
    confirmed_previous: dict[str, Any] | None,
) -> str:
    previous = (confirmed_previous or {}).get("summary") or {}
    previous_text = previous.get("period", "") if previous else "（首次报告，无上周期摘要）"
    if previous:
        previous_text += f"（{len(previous.get('real_progress') or [])} 项进展、{len(previous.get('risks') or [])} 项风险）"
    blocks = _assemble_blocks(audit, experiments)
    return _REPORT_USER_TEMPLATE.format(
        previous_summary=previous_text,
        blocks=blocks,
        style_hint=_memory_style_banner() or "（无）",
    )


def build_mentor_report(
    intelligence: Any,
    project: Any,
    *,
    baseline_revision: int | None = None,
    legacy_out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """收集确定性数据并组织成模板段落（零模型调用）。"""
    audit = build_cycle_audit(
        intelligence,
        project,
        baseline_revision=baseline_revision,
        legacy_out_dir=legacy_out_dir,
    )
    if not audit.get("ok"):
        return audit
    experiments: list[dict[str, Any]] = []
    try:
        from .experiments import ExperimentRepository

        experiments = ExperimentRepository(intelligence.db).list_period(
            project.id,
            start=float(audit["baseline"].get("created_at") or 0),
            end=float(audit["current"].get("created_at") or 0),
        )
    except Exception:
        experiments = []
    confirmed = latest_confirmed_summary(intelligence, project.id)
    prompt = _prompt_for(audit, experiments, confirmed)
    return {
        "ok": True,
        "project_id": project.id,
        "baseline": audit["baseline"],
        "current": audit["current"],
        "period": audit["period"],
        "claims": audit.get("real_progress") or [],
        "experiments": experiments,
        "risks": audit.get("risks") or [],
        "failed_experiments": audit.get("failed_experiments") or [],
        "candidates": audit.get("next_cycle_candidates") or [],
        "confirmed_previous": confirmed,
        "data_block": _assemble_blocks(audit, experiments),
        "prompt": prompt,
        "report": "",
        "unsupported": [],
        "generated_at": _utc_iso(),
    }


def validate_report_text(report: str, data: dict[str, Any]) -> list[str]:
    """确定性校验：报告内每个数字/哈希必须能在数据区原文中找到（D2/D4）。

    返回失败项列表；空列表 = 通过。未登记数字即视为模型编造（D4）。
    """
    problems: list[str] = []
    data_text = "\n".join([
        str(data.get("data_block") or ""),
        *(json.dumps(entry, ensure_ascii=False) for entry in (data.get("experiments") or [])),
        *(json.dumps(claim, ensure_ascii=False) for claim in (data.get("claims") or [])),
    ])
    numbers = set(re.findall(r"\d+(?:\.\d+)?", data_text or ""))
    report_numbers = re.findall(r"-?\d+(?:\.\d+)?", report)
    for number in report_numbers:
        if number.lstrip("-").startswith("0") and number.lstrip("-") not in {"0", "0.0"}:
            continue
        if number.lstrip("-") not in numbers:
            problems.append(f"报告中的数值 {number} 无法在数据区回溯")
    hashes = set(re.findall(r"\b[0-9a-f]{8,64}\b", data_text or ""))
    for digest in set(re.findall(r"\b[0-9a-f]{8,64}\b", report)) - hashes:
        problems.append(f"报告中的哈希 {digest[:12]}… 无法在数据区回溯")
    return problems


def generate_mentor_report(
    data: dict[str, Any],
    *,
    llm: Any | None = None,
    llm_invoke: Callable[[list[Any]], Any] | None = None,
) -> tuple[str, list[str]]:
    """LLM 仅组织语言；输出后确定性校验。返回 (报告, 失败项列表)。

    无模型 / LLM 失败时回退为数据块确定性呈现（数字 100% 可回溯）。
    """
    if llm is not None or llm_invoke is not None:
        try:
            invoker = llm_invoke or llm.invoke
            response = invoker([
                {"role": "system", "content": _REPORT_SYSTEM},
                {"role": "user", "content": str(data.get("prompt") or "")},
            ])
            text = str(getattr(response, "content", response) or "").strip()
            if text:
                problems = validate_report_text(text, data)
                return text, problems
        except Exception:
            pass
    deterministic = _deterministic_fallback(data)
    return deterministic, []


def _deterministic_fallback(data: dict[str, Any]) -> str:
    lines = [
        f"# 导师周报草稿（确定性回退）",
        "",
        f"周期：{data.get('period', '')}",
        "",
        "## 本周期进展（证据可追溯）",
        "",
    ]
    for claim in data.get("claims") or []:
        refs = " ".join(f"<{ref}>" for ref in (claim.get("evidence_refs") or [])[:5])
        lines.append(f"- {claim.get('summary')} {refs}")
    experiments = data.get("experiments") or []
    if experiments:
        lines.extend(["", "## 实验记录", ""])
        for item in experiments:
            metrics = "、".join(f"{k}={v}" for k, v in sorted((item.get("metrics") or {}).items())[:5])
            lines.append(f"- [{item.get('status')}] {item.get('name')} <exp:{item.get('id')}> {metrics}")
    risks = data.get("risks") or []
    failed = data.get("failed_experiments") or []
    if risks or failed:
        lines.extend(["", "## 风险与失败", ""])
        lines.extend(f"- {item}" for item in risks[:12])
        lines.extend(f"- {item.get('summary')}" for item in failed[:12])
    candidates = data.get("candidates") or []
    if candidates:
        lines.extend(["", "## 下一步建议", ""])
        lines.extend(f"- {item.get('summary')}" for item in candidates[:10])
    lines.extend(["", "## 数据清单", ""])
    lines.append("```text")
    lines.append(str(data.get("data_block") or "（无数据）"))
    lines.append("```")
    return "\n".join(lines).rstrip() + "\n"


def export_mentor_report_markdown(
    data: dict[str, Any],
    report: str,
    *,
    out_dir: str | Path,
) -> dict[str, str]:
    """导出 mentor_report.md + mentor_report.json（幂等重写）。"""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / "mentor_report.md"
    json_path = root / "mentor_report.json"
    markdown_path.write_text(report, encoding="utf-8")
    payload = dict(data)
    payload["report"] = report
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return {"markdown_path": str(markdown_path), "json_path": str(json_path)}


def confirm_mentor_report(
    intelligence: Any,
    project: Any,
    *,
    report: str,
    baseline_revision: int | None = None,
    legacy_out_dir: str | Path | None = None,
    out_dir: str | Path | None = None,
    llm: Any | None = None,
    llm_invoke: Callable[[list[Any]], Any] | None = None,
) -> dict[str, Any]:
    """确认并导出导师周报：数据构建 → LLM 组织 → 校验 → （无则导出）。

    校验失败时返回 failures 而不导出（整段退回语义，D2）。
    """
    data = build_mentor_report(
        intelligence,
        project,
        baseline_revision=baseline_revision,
        legacy_out_dir=legacy_out_dir,
    )
    if not data.get("ok"):
        return data
    if baseline is None and report is None:
        pass
    if report is not None and report.strip():
        failures = validate_report_text(report, data)
        if failures:
            return {
                "ok": False,
                "error": "周报校验失败（整段退回）",
                "failures": failures,
                "report": report,
            }
    else:
        report, failures = generate_mentor_report(data, llm=llm, llm_invoke=llm_invoke)
        if failures:
            return {
                "ok": False,
                "error": "LLM 周报校验失败（整段退回）",
                "failures": failures,
                "report": report,
            }
    artifacts = export_mentor_report_markdown(data, report, out_dir=out_dir or Path("reports/progress"))
    data["report"] = report
    data["artifacts"] = artifacts
    data["confirmed_at"] = _utc_iso()
    return {"ok": True, **data, "artifacts": artifacts}