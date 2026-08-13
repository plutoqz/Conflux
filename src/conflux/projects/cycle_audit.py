"""P3.5 cycle audit — snapshot comparator and confirmed cycle summaries.

Replaces the directory-scanning ``progress_audit`` with a comparison of two
immutable ``ProjectContextSnapshot`` revisions plus the period events between
them (plan §6.3/§10.7).  Design rules from the frozen plan:

- 真实进展 claims always carry evidence refs; file counts, document index
  changes and model judgments are weak signals, never packaged as progress.
- The comparator reads materialized state only — no directory scan, no model,
  no remote check.
- 周期摘要 is only persisted after explicit user confirmation; the latest
  confirmed summary's ``current_revision`` becomes the next audit baseline.
- Legacy ``progress_audit`` snapshots are either migrated (Git head) or
  explicitly marked ``incomparable`` (plan P3.5 acceptance).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .repository import ProjectIntelligence

# Claim categories, ordered by weight for stable output.
_CATEGORY_ORDER = ["work_item", "commit", "test", "experiment", "paper", "evidence"]

# Evidence refs that count as supporting a work item (mirrors link_service).
_SUPPORTING_MARKER = ":supports:"


def _utc_date(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return "?"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _period_events(
    intelligence: ProjectIntelligence,
    project_id: str,
    start: float,
    end: float,
    *,
    max_events: int = 10000,
) -> list[dict[str, Any]]:
    """Events with ``start < created_at <= end``, paginated by event id."""
    matched: list[dict[str, Any]] = []
    cursor = 0
    while len(matched) < max_events:
        events = intelligence.events.list(project_id, after_event_id=cursor, limit=500)
        if not events:
            return matched
        for event in events:
            created = float(event.get("created_at") or 0)
            if created > end:
                return matched
            if start < created:
                matched.append(event)
        cursor = max(int(event["event_id"]) for event in events)
    return matched


def latest_confirmed_summary(
    intelligence: ProjectIntelligence,
    project_id: str,
) -> dict[str, Any] | None:
    """Latest confirmed cycle summary (row envelope + inner summary)."""
    return intelligence.cycles.latest_confirmed(project_id)


def baseline_revision_for(intelligence: ProjectIntelligence, project_id: str) -> int | None:
    """Revision the next audit compares against, or None for a first baseline."""
    confirmed = intelligence.cycles.latest_confirmed(project_id)
    if confirmed is None:
        return None
    return int(confirmed["current_revision"])


def _load_legacy_baseline(legacy_out_dir: str | Path | None) -> dict[str, Any] | None:
    """Import the legacy directory-scan snapshot (progress_audit JSON).

    Only the Git head is comparable against a P3 snapshot; the caller marks
    every other dimension as incomparable.  Returns None when the file is
    absent or broken beyond import.
    """
    if not legacy_out_dir:
        return None
    path = Path(legacy_out_dir) / "project_snapshot.json"
    if not path.exists():
        return None
    try:
        from conflux.progress_audit.models import ProjectSnapshot

        legacy = ProjectSnapshot.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"path": str(path), "git_head": "", "importable": False}
    if not legacy.git_head:
        return {"path": str(path), "git_head": "", "importable": False}
    return {
        "path": str(path),
        "git_head": legacy.git_head,
        "captured_at": legacy.captured_at.isoformat(),
        "source": "progress_audit.project_snapshot",
        "importable": True,
    }


def _snapshot_risks(current: dict[str, Any], period_events: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    git = current.get("git_state") or {}
    dirty = int(git.get("dirty_files") or 0)
    if dirty:
        risks.append(f"Git 工作区存在 {dirty} 个未提交文件。")
    if str(current.get("health") or "ok") == "warning":
        risks.append("项目状态标记为需关注（含受阻工作项、失败运行或未提交变更）。")
    tests = (current.get("run_state") or {}).get("tests") or []
    if tests:
        latest_test = max(tests, key=lambda t: float(t.get("checked_at") or 0))
        if str(latest_test.get("status") or "") == "failed":
            risks.append(f"测试命令失败（退出码 {latest_test.get('exit_code')}）：{latest_test.get('command')}")
        elif str(latest_test.get("status") or "") in {"timed_out", "error"}:
            risks.append(f"测试命令无法完成：{latest_test.get('command')}")
    return _dedupe(risks)


def _work_item_risks(current: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    for item in current.get("work_items") or []:
        declared = str(item.get("declared_status") or "")
        observed = str(item.get("observed_status") or "")
        evidence = item.get("evidence_refs") or []
        title = str(item.get("title") or "")
        if declared == "completed" and not evidence:
            risks.append(f"工作项「{title}」标记为已完成，但没有关联证据。")
        elif observed == "failed":
            risks.append(f"工作项「{title}」的证据包含不支持结论。")
    return risks


def _new_items(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, dict[str, Any]]:
    baseline_items = {str(i.get("work_item_id") or ""): i for i in baseline.get("work_items") or []}
    return {
        str(i.get("work_item_id") or ""): i
        for i in current.get("work_items") or []
        if str(i.get("work_item_id") or "") not in baseline_items
    }


def _diff_work_items(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    """Status/evidence/acceptance changes between two snapshots.

    Returns (claims, acceptance_updates, risks, weak_signals).  Completion
    without supporting evidence is a risk, never a claim.
    """
    baseline_items = {str(i.get("work_item_id") or ""): i for i in baseline.get("work_items") or []}
    claims: list[dict[str, Any]] = []
    acceptance_updates: list[dict[str, Any]] = []
    risks: list[str] = []
    weak: list[str] = []
    for item in current.get("work_items") or []:
        work_item_id = str(item.get("work_item_id") or "")
        title = str(item.get("title") or "")
        previous = baseline_items.get(work_item_id)
        if previous is None:
            continue
        declared_before = str(previous.get("declared_status") or "")
        declared_now = str(item.get("declared_status") or "")
        observed_before = str(previous.get("observed_status") or "")
        observed_now = str(item.get("observed_status") or "")
        evidence_before = {str(ref) for ref in (previous.get("evidence_refs") or [])}
        evidence_now = {str(ref) for ref in (item.get("evidence_refs") or [])}
        new_evidence = sorted(evidence_now - evidence_before)
        new_supporting = [ref for ref in new_evidence if _SUPPORTING_MARKER in ref]
        criteria_before = list(previous.get("acceptance_criteria") or [])
        criteria_now = list(item.get("acceptance_criteria") or [])
        new_runs = sorted({
            str(run_id) for run_id in (item.get("linked_run_ids") or [])
        } - {
            str(run_id) for run_id in (previous.get("linked_run_ids") or [])
        })
        new_papers = sorted({
            str(key) for key in (item.get("linked_paper_keys") or [])
        } - {
            str(key) for key in (previous.get("linked_paper_keys") or [])
        })
        changed = (
            declared_before != declared_now
            or observed_before != observed_now
            or new_evidence or new_runs or new_papers or criteria_before != criteria_now
        )
        if not changed:
            continue

        update = {
            "work_item_id": work_item_id,
            "kind": str(item.get("kind") or ""),
            "title": title,
            "declared": {"before": declared_before, "now": declared_now},
            "observed": {"before": observed_before, "now": observed_now},
            "acceptance_criteria": criteria_now,
            "criteria_changed": criteria_before != criteria_now,
            "new_evidence_refs": new_evidence,
            "new_run_ids": new_runs,
            "new_paper_keys": new_papers,
        }
        acceptance_updates.append(update)

        refs = _dedupe(new_supporting + [f"run:{run_id}" for run_id in new_runs]
                        + [f"paper:{key}" for key in new_papers])
        if declared_now == "completed":
            if new_supporting:
                claims.append({
                    "category": "work_item",
                    "work_item_id": work_item_id,
                    "summary": f"工作项「{title}」完成（{len(new_supporting)} 条支持证据）",
                    "evidence_refs": refs,
                    "acceptance_criteria": criteria_now,
                })
            elif refs:
                claims.append({
                    "category": "work_item",
                    "work_item_id": work_item_id,
                    "summary": f"工作项「{title}」完成（运行/论文关联，证据待确认）",
                    "evidence_refs": refs,
                    "acceptance_criteria": criteria_now,
                })
            else:
                risks.append(f"工作项「{title}」标记为已完成，但没有关联证据。")
        elif observed_now == "verified" and new_supporting:
            claims.append({
                "category": "work_item",
                "work_item_id": work_item_id,
                "summary": f"工作项「{title}」获得验证证据",
                "evidence_refs": refs,
                "acceptance_criteria": criteria_now,
            })
        elif declared_now == "blocked" and declared_before != "blocked":
            risks.append(f"工作项「{title}」被标记为受阻。")
        elif new_supporting:
            claims.append({
                "category": "work_item",
                "work_item_id": work_item_id,
                "summary": f"工作项「{title}」新增 {len(new_supporting)} 条支持证据",
                "evidence_refs": refs,
                "acceptance_criteria": criteria_now,
            })
        elif refs:
            claims.append({
                "category": "work_item",
                "work_item_id": work_item_id,
                "summary": f"工作项「{title}」新增运行/论文关联",
                "evidence_refs": refs,
                "acceptance_criteria": criteria_now,
            })
        else:
            weak.append(
                f"工作项「{title}」状态变化缺少可归因证据（{declared_before} → {declared_now}）。"
            )
    return claims, acceptance_updates, risks, weak


def _diff_git(
    baseline: dict[str, Any],
    current: dict[str, Any],
    period_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_git = baseline.get("git_state") or {}
    current_git = current.get("git_state") or {}
    head_before = str(baseline_git.get("head") or "")
    head_now = str(current_git.get("head") or "")
    if not head_now or head_now == head_before:
        return []
    subjects: list[str] = []
    for event in reversed(period_events):
        if str(event.get("kind") or "") == "git.head_changed":
            subjects = [
                str(subject) for subject in (event.get("payload") or {}).get("recent_subjects") or []
            ]
            break
    summary = f"Git 头更新：{head_now[:12]}"
    if subjects:
        summary += f"（{subjects[0]}）"
    return [{"category": "commit", "summary": summary, "evidence_refs": [f"git:{head_now[:16]}"]}]


def _diff_tests(
    baseline: dict[str, Any],
    current: dict[str, Any],
    period_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    baseline_tests = {(
        str(t.get("command") or ""),
        str(t.get("head") or ""),
        str(t.get("status") or ""),
        t.get("exit_code"),
    ) for t in (baseline.get("run_state") or {}).get("tests") or []}
    claims: list[dict[str, Any]] = []
    risks: list[str] = []
    for test in (current.get("run_state") or {}).get("tests") or []:
        key = (
            str(test.get("command") or ""),
            str(test.get("head") or ""),
            str(test.get("status") or ""),
            test.get("exit_code"),
        )
        if key in baseline_tests:
            continue
        command = str(test.get("command") or "")
        head = str(test.get("head") or "")
        status = str(test.get("status") or "")
        if status == "passed":
            claims.append({
                "category": "test",
                "summary": f"测试命令通过：{command}",
                "evidence_refs": [f"test:{command}@{head[:8]}"],
            })
        elif status == "failed":
            risks.append(f"测试命令失败（退出码 {test.get('exit_code')}）：{command}")
        elif status in {"timed_out", "error"}:
            risks.append(f"测试命令无法完成：{command}")
    return claims, risks


def _diff_runs(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Research query runs: completed runs are progress, failures are risks."""
    baseline_runs = {
        str(run.get("run_id") or ""): run
        for run in (baseline.get("run_state") or {}).get("runs") or []
    }
    claims: list[dict[str, Any]] = []
    query_changes: list[dict[str, Any]] = []
    risks: list[str] = []
    for run in (current.get("run_state") or {}).get("runs") or []:
        run_id = str(run.get("run_id") or "")
        if not run_id or run_id in baseline_runs:
            continue
        status = str(run.get("status") or "")
        entry = {
            "run_id": run_id,
            "status": status,
            "work_item_id": str(run.get("work_item_id") or ""),
            "elapsed_seconds": run.get("elapsed_seconds"),
            "tokens": run.get("tokens"),
        }
        query_changes.append(entry)
        if status == "failed":
            risks.append(f"研究运行失败：{run_id}")
        else:
            claims.append({
                "category": "experiment",
                "run_id": run_id,
                "summary": f"研究运行完成：{run_id}",
                "evidence_refs": [f"run:{run_id}"],
            })
    return claims, query_changes, risks


def _diff_radar(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    before = baseline.get("research_state") or {}
    now = current.get("research_state") or {}
    run_before = str((before.get("radar") or {}).get("run_id") or "")
    run_now = str((now.get("radar") or {}).get("run_id") or "")
    if not run_now or run_now == run_before:
        return []
    return [{
        "category": "paper",
        "summary": f"论文雷达完成运行：{run_now}",
        "evidence_refs": [f"radar:{run_now}"],
    }]


def _diff_evidence(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_sources = {
        str(source.get("source_id") or ""): source
        for source in (baseline.get("evidence_state") or {}).get("sources") or []
    }
    claims: list[dict[str, Any]] = []
    for source in (current.get("evidence_state") or {}).get("sources") or []:
        source_id = str(source.get("source_id") or "")
        if not source_id or source_id in baseline_sources:
            continue
        status = str(source.get("status") or "")
        claims.append({
            "category": "evidence",
            "summary": f"证据来源变化：{source_id}" + (f"（{status}）" if status else ""),
            "evidence_refs": [f"source:{source_id}"],
        })
    return claims


def _diff_papers(
    intelligence: ProjectIntelligence,
    project_id: str,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Paper changes from the project paper store, restricted to the period."""
    claims: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    try:
        from conflux.adapters.sqlite_store import ProjectPaperStore

        papers = ProjectPaperStore(intelligence.db).list(project_id)
    except Exception:
        return claims, changes
    start = float(baseline.get("created_at") or 0)
    end = float(current.get("created_at") or 0)
    # Current linked keys per work item, for change attribution.
    linked_by_item: dict[str, list[str]] = {}
    for item in current.get("work_items") or []:
        for key in (item.get("linked_paper_keys") or []):
            linked_by_item.setdefault(str(key), []).append(
                str(item.get("work_item_id") or "")
            )
    for paper in papers or []:
        status = str(paper.get("status") or "")
        if status not in {"saved", "shortlisted"}:
            continue
        changed_at = float(paper.get("updated_at") or 0)
        if not (start < changed_at <= end):
            continue
        paper_key = str(paper.get("paper_key") or "")
        if not paper_key:
            continue
        title = str((paper.get("metadata") or {}).get("title") or paper_key)
        changes.append({
            "paper_key": paper_key,
            "title": title,
            "status": status,
            "changed_at": changed_at,
            "work_item_ids": linked_by_item.get(paper_key, []),
        })
        if status == "saved":
            claims.append({
                "category": "paper",
                "summary": f"论文已保存：{title}",
                "evidence_refs": [f"paper:{paper_key}"],
            })
    return claims, changes


def _diff_documents(
    baseline: dict[str, Any],
    current: dict[str, Any],
    period_events: list[dict[str, Any]],
) -> list[str]:
    """Document index changes are weak signals, never progress (plan §4.2)."""
    version_before = str(baseline.get("document_index_version") or "")
    version_now = str(current.get("document_index_version") or "")
    if version_now and version_now != version_before:
        paths: list[str] = []
        for event in period_events:
            kind = str(event.get("kind") or "")
            if kind in {"document.changed", "document.discovered"}:
                path = str((event.get("payload") or {}).get("path") or "")
                if path and path not in paths:
                    paths.append(path)
        detail = f"（{', '.join(paths[:3])}{' 等' if len(paths) > 3 else ''}）" if paths else ""
        return [f"文档索引更新至 {version_now[:12]}，共 {len(paths)} 个变更文件{detail}；文档数量变化不代表完成。"]
    return []


def _next_cycle_candidates(
    intelligence: ProjectIntelligence,
    project_id: str,
    current: dict[str, Any],
    *,
    failed_runs: list[dict[str, Any]],
    legacy: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    items = current.get("work_items") or []
    for item in items:
        title = str(item.get("title") or "")
        work_item_id = str(item.get("work_item_id") or "")
        declared = str(item.get("declared_status") or "")
        evidence = item.get("evidence_refs") or []
        if declared == "blocked":
            candidates.append({
                "kind": "unblock",
                "work_item_id": work_item_id,
                "summary": f"解除工作项「{title}」的阻塞",
            })
        elif declared == "in_progress" and not evidence:
            candidates.append({
                "kind": "evidence",
                "work_item_id": work_item_id,
                "summary": f"为进行中的「{title}」补充可验证证据",
            })
        elif declared == "completed" and not evidence:
            candidates.append({
                "kind": "evidence",
                "work_item_id": work_item_id,
                "summary": f"为已完成但无证据的「{title}」补齐证据或复核状态",
            })
    for run in failed_runs[:3]:
        candidates.append({
            "kind": "retry",
            "run_id": run.get("run_id"),
            "summary": f"调查并重试失败的研究运行 {run.get('run_id')}",
        })
    for review in intelligence.reviews.list(project_id, status="pending")[:3]:
        candidates.append({
            "kind": "review",
            "review_id": review.review_id,
            "summary": f"处理待复核：{review.summary}",
        })
    if legacy:
        candidates.append({
            "kind": "baseline",
            "summary": "确认当前快照为新基线，结束旧基线的不可比维度",
        })
    return candidates[:8]


def _empty_draft(project_id: str, error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "project_id": project_id,
        "error": error,
    }


def build_cycle_audit(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    baseline_revision: int | None = None,
    legacy_out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Compare the latest snapshot against the selected baseline.

    ``baseline_revision`` explicitly pins a snapshot revision; otherwise the
    latest confirmed cycle summary selects the baseline, a legacy
    ``progress_audit`` snapshot is imported (Git head only), or the audit
    reports a first baseline (``created``).
    """
    project_id = project.id
    latest = intelligence.snapshots.latest(project_id)
    if latest is None:
        return _empty_draft(project_id, "尚未建立快照：先运行一次检查状态或登记后刷新。")

    baseline = None
    legacy = None
    baseline_status = "created"
    if baseline_revision is not None and baseline_revision > 0:
        baseline = intelligence.snapshots.get(project_id, int(baseline_revision))
        if baseline is None:
            return _empty_draft(project_id, f"基线快照不存在：v{baseline_revision}")
        if baseline.revision > latest.revision:
            return _empty_draft(
                project_id,
                f"基线 v{baseline.revision} 晚于当前快照 v{latest.revision}。",
            )
        baseline_status = "compared"
    else:
        confirmed = intelligence.cycles.latest_confirmed(project_id)
        if confirmed is not None:
            revision = int(confirmed["current_revision"])
            baseline = intelligence.snapshots.get(project_id, revision)
            if baseline is None:
                return _empty_draft(
                    project_id,
                    f"已确认摘要引用的基线快照缺失：v{revision}",
                )
            baseline_status = "compared"
        else:
            legacy = _load_legacy_baseline(legacy_out_dir)
            if legacy is not None and not legacy.get("importable"):
                baseline_status = "incomparable"
                legacy = None
            elif legacy is not None:
                baseline_status = "legacy"
            else:
                baseline = latest
                baseline_status = "created"

    baseline_payload: dict[str, Any]
    if baseline_status == "incomparable":
        baseline_payload = {
            "revision": 0,
            "created_at": 0.0,
            "snapshot_id": "",
        }
    elif baseline_status == "legacy":
        baseline_payload = {
            "revision": 0,
            "created_at": 0.0,
            "snapshot_id": "",
            "legacy": legacy,
        }
    else:
        baseline_payload = {
            "revision": baseline.revision,
            "created_at": baseline.created_at,
            "snapshot_id": baseline.snapshot_id,
        }

    current_payload = latest.model_dump()
    if baseline_status == "legacy":
        base_for_diff: dict[str, Any] = {
            "git_state": {"head": str(legacy["git_head"])},
            "created_at": 0.0,
        }
    elif baseline_status == "incomparable":
        base_for_diff = {"created_at": 0.0}
    else:
        base_for_diff = baseline.model_dump()

    if baseline_status == "compared" and baseline is not None and baseline.revision == latest.revision:
        baseline_status = "unchanged"

    period_events = _period_events(
        intelligence, project_id,
        start=float(baseline_payload["created_at"] or 0),
        end=float(latest.created_at),
    )

    claims: list[dict[str, Any]] = []
    weak_signals: list[str] = []
    risks: list[str] = []
    query_changes: list[dict[str, Any]] = []
    paper_changes: list[dict[str, Any]] = []
    acceptance_updates: list[dict[str, Any]] = []

    if baseline_status in {"created", "unchanged"}:
        weak_signals.append(
            "首次基线：本次仅记录当前状态，不判断真实进展。"
            if baseline_status == "created"
            else "与基线快照相同，本周期未检测到新变化。"
        )
        risks.extend(_snapshot_risks(current_payload, period_events))
        risks.extend(_work_item_risks(current_payload))
    elif baseline_status == "incomparable":
        weak_signals.append(
            "旧基线（目录扫描版 project_snapshot.json）无法迁移：缺少可比较的 Git 头；"
            "本次不判断进展，确认当前快照后以新基线重新开始。"
        )
        risks.extend(_snapshot_risks(current_payload, period_events))
        risks.extend(_work_item_risks(current_payload))
    elif baseline_status == "legacy":
        git_claims = _diff_git(base_for_diff, current_payload, period_events)
        claims.extend(git_claims)
        if git_claims:
            weak_signals.append(
                "旧基线（目录扫描版）仅迁移了 Git 头，测试/实验/报告/查询/论文维度不可比较；"
                "确认当前快照后可建立完整新基线。"
            )
        else:
            weak_signals.append(
                "旧基线（目录扫描版）仅迁移了 Git 头，且头未变化；其余维度不可比较。"
            )
        risks.extend(_snapshot_risks(current_payload, period_events))
        risks.extend(_work_item_risks(current_payload))
    else:
        claims.extend(_diff_git(base_for_diff, current_payload, period_events))
        test_claims, test_risks = _diff_tests(base_for_diff, current_payload, period_events)
        claims.extend(test_claims)
        risks.extend(test_risks)
        run_claims, query_changes, run_risks = _diff_runs(base_for_diff, current_payload)
        claims.extend(run_claims)
        risks.extend(run_risks)
        claims.extend(_diff_radar(base_for_diff, current_payload))
        claims.extend(_diff_evidence(base_for_diff, current_payload))
        paper_claims, paper_changes = _diff_papers(
            intelligence, project_id, base_for_diff, current_payload
        )
        claims.extend(paper_claims)
        item_claims, acceptance_updates, item_risks, item_weak = _diff_work_items(
            base_for_diff, current_payload
        )
        claims.extend(item_claims)
        risks.extend(item_risks)
        weak_signals.extend(item_weak)
        weak_signals.extend(_diff_documents(base_for_diff, current_payload, period_events))
        risks.extend(_snapshot_risks(current_payload, period_events))
        # Standing risks carried across cycles (e.g. completed without evidence).
        risks.extend(_work_item_risks(current_payload))
        if not claims and not weak_signals:
            weak_signals.append("相对基线未检测到可归因的新提交、测试、实验、查询或论文变化。")

    failed_runs = [
        entry for entry in query_changes if str(entry.get("status") or "") == "failed"
    ]
    failed_experiments: list[dict[str, Any]] = []
    for entry in failed_runs:
        failed_experiments.append({
            "run_id": entry.get("run_id"),
            "work_item_id": entry.get("work_item_id"),
            "summary": f"研究运行失败：{entry.get('run_id')}",
            "evidence_refs": [f"run:{entry.get('run_id')}"],
        })
    for item in current_payload.get("work_items") or []:
        if str(item.get("observed_status") or "") == "failed":
            failed_experiments.append({
                "work_item_id": str(item.get("work_item_id") or ""),
                "summary": f"工作项证据不支持结论：「{item.get('title')}」",
                "evidence_refs": [
                    ref for ref in (item.get("evidence_refs") or [])
                    if ":contradicts:" in ref or ":insufficient:" in ref
                ],
            })

    claims.sort(key=lambda claim: _CATEGORY_ORDER.index(
        claim["category"] if claim["category"] in _CATEGORY_ORDER else "work_item"
    ))
    evidence_refs = _dedupe(ref for claim in claims for ref in claim.get("evidence_refs") or [])
    next_candidates = _next_cycle_candidates(
        intelligence,
        project_id,
        current_payload,
        failed_runs=failed_experiments,
        legacy=baseline_status in {"legacy", "incomparable"},
    )
    return {
        "ok": True,
        "project_id": project_id,
        "baseline_status": baseline_status,
        "baseline": baseline_payload,
        "current": {
            "revision": latest.revision,
            "created_at": latest.created_at,
            "snapshot_id": latest.snapshot_id,
        },
        "period": f"{_utc_date(float(baseline_payload['created_at'] or 0))} 至 {_utc_date(latest.created_at)}",
        "real_progress": claims,
        "weak_signals": _dedupe(weak_signals),
        "risks": _dedupe(risks),
        "failed_experiments": failed_experiments,
        "query_changes": query_changes,
        "paper_changes": paper_changes,
        "acceptance_updates": acceptance_updates,
        "next_cycle_candidates": next_candidates,
        "evidence_refs": evidence_refs,
        "confirmed": False,
        "summary_id": "",
    }


def confirm_cycle_summary(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    baseline_revision: int | None = None,
    current_revision: int | None = None,
    legacy_out_dir: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Confirm a cycle summary; its current revision becomes the new baseline.

    Idempotent: the same (baseline, current) pair always maps to the same
    summary id, and the Markdown/JSON artifacts are rewritten deterministically.
    """
    project_id = project.id
    draft = build_cycle_audit(
        intelligence,
        project,
        baseline_revision=baseline_revision,
        legacy_out_dir=legacy_out_dir,
    )
    if not draft.get("ok"):
        return draft
    latest = intelligence.snapshots.latest(project_id)
    if latest is None:
        return _empty_draft(project_id, "尚未建立快照，无法确认周期摘要。")
    if current_revision is not None and int(current_revision) != latest.revision:
        return {
            "ok": False,
            "project_id": project_id,
            "error": f"当前快照已更新为 v{latest.revision}，请重新生成摘要后再确认。",
        }
    baseline = draft["baseline"]
    summary_id = f"cycle-{project_id}-{int(baseline['revision'])}-{latest.revision}"
    payload = dict(draft)
    payload["ok"] = True
    payload["confirmed"] = True
    payload["summary_id"] = summary_id
    payload["confirmed_at"] = latest.created_at
    intelligence.cycles.save(
        {
            "summary_id": summary_id,
            "project_id": project_id,
            "baseline_revision": int(baseline["revision"]),
            "current_revision": latest.revision,
            "period_start": float(baseline["created_at"] or 0),
            "period_end": float(latest.created_at),
            "summary": payload,
        },
        status="confirmed",
    )
    artifacts = write_cycle_artifacts(payload, out_dir=out_dir, project_id=project_id)
    payload["artifacts"] = {
        "markdown_path": str(artifacts["markdown_path"]),
        "json_path": str(artifacts["json_path"]),
    }
    return payload


def build_cycle_markdown(summary: dict[str, Any]) -> str:
    """Markdown export for a cycle summary (progress_audit-compatible shape)."""
    lines = [
        f"# 周期摘要：{summary.get('project_id')}",
        "",
        "## 摘要",
        f"- 周期：{summary.get('period')}",
        f"- 基线：v{summary.get('baseline', {}).get('revision', 0)}（`{summary.get('baseline_status')}`）",
        f"- 当前：v{summary.get('current', {}).get('revision', 0)}",
        f"- 真实进展：{len(summary.get('real_progress') or [])}",
        f"- 失败实验：{len(summary.get('failed_experiments') or [])}",
        f"- 风险：{len(summary.get('risks') or [])}",
        "",
        "## 真实进展",
        "",
    ]
    for claim in summary.get("real_progress") or []:
        lines.append(f"- [{claim.get('category')}] {claim.get('summary')}")
        lines.extend(f"  - 证据：`{ref}`" for ref in (claim.get("evidence_refs") or []))
        for criterion in (claim.get("acceptance_criteria") or [])[:5]:
            lines.append(f"  - 验收标准：{criterion}")
    if not summary.get("real_progress"):
        lines.append("- 本周期尚无可验证的真实进展。")
    for title, key, empty in (
        ("失败实验", "failed_experiments", "本周期没有失败实验。"),
        ("论文变化", "paper_changes", "本周期没有论文变化。"),
        ("查询变化", "query_changes", "本周期没有研究查询变化。"),
        ("弱信号", "weak_signals", "未检测到弱信号。"),
        ("风险", "risks", "当前未检测到风险。"),
        ("下一周期候选", "next_cycle_candidates", "暂无候选。"),
    ):
        lines.extend(["", f"## {title}", ""])
        entries = summary.get(key) or []
        for entry in entries:
            lines.append(f"- {entry.get('summary') if isinstance(entry, dict) else entry}")
        if not entries:
            lines.append(f"- {empty}")
    return "\n".join(lines).rstrip() + "\n"


def write_cycle_artifacts(
    summary: dict[str, Any],
    *,
    out_dir: str | Path | None,
    project_id: str,
) -> dict[str, str]:
    """Persist cycle_summary.md / cycle_summary.json next to legacy outputs."""
    root = Path(out_dir) if out_dir else Path("reports/progress")
    target = root / str(project_id)
    target.mkdir(parents=True, exist_ok=True)
    markdown_path = target / "cycle_summary.md"
    json_path = target / "cycle_summary.json"
    markdown_path.write_text(build_cycle_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "markdown_path": str(markdown_path),
        "json_path": str(json_path),
    }
