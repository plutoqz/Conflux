"""Build project snapshots and evidence-backed progress audit reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .artifact_inspector import changed_artifacts, inspect_artifacts
from .git_inspector import inspect_git
from .models import ProgressAuditReport, ProgressClaim, ProjectSnapshot, utc_now
from .report_inspector import summarize_report
from .test_inspector import inspect_tests


def create_project_snapshot(
    project_path: str | Path,
    *,
    project_id: str = "",
    test_command: str | list[str] | None = None,
    result_dirs: Iterable[str] = ("results", "artifacts", "experiments"),
    report_dirs: Iterable[str] = ("reports",),
    test_timeout_seconds: int = 120,
) -> ProjectSnapshot:
    root = Path(project_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"项目路径不存在或不是目录：{root}")

    git = inspect_git(root)
    results, reports = inspect_artifacts(
        root,
        result_dirs=result_dirs,
        report_dirs=report_dirs,
    )
    tests = inspect_tests(root, test_command, timeout_seconds=test_timeout_seconds)
    return ProjectSnapshot(
        project_id=project_id or _project_id(root.name),
        path=str(root),
        captured_at=utc_now(),
        git_available=git.is_repository,
        git_root=git.root,
        git_branch=git.branch,
        git_head=git.head,
        dirty_files=git.dirty_files,
        recent_commits=git.recent_commits,
        test_result=tests,
        result_files=results,
        report_files=reports,
        errors=git.errors,
    )


def audit_project(
    project_path: str | Path,
    *,
    baseline: ProjectSnapshot | None = None,
    project_id: str = "",
    test_command: str | list[str] | None = None,
    result_dirs: Iterable[str] = ("results", "artifacts", "experiments"),
    report_dirs: Iterable[str] = ("reports",),
    test_timeout_seconds: int = 120,
) -> ProgressAuditReport:
    current = create_project_snapshot(
        project_path,
        project_id=project_id or (baseline.project_id if baseline else ""),
        test_command=test_command,
        result_dirs=result_dirs,
        report_dirs=report_dirs,
        test_timeout_seconds=test_timeout_seconds,
    )
    return compare_snapshots(current, baseline)


def compare_snapshots(
    current: ProjectSnapshot,
    baseline: ProjectSnapshot | None,
) -> ProgressAuditReport:
    if baseline is None:
        risks = _snapshot_risks(current)
        actions = ["完成一轮代码、实验或报告工作后再次运行审计，以生成周期对比。"]
        if risks:
            actions.insert(0, "先处理当前基线中暴露的风险，再开始下一工作周期。")
        return ProgressAuditReport(
            project_id=current.project_id,
            period=f"首次基线 · {current.captured_at.date().isoformat()}",
            captured_at=current.captured_at,
            baseline_status="created",
            weak_signals=["尚无历史基线；本次仅记录当前状态，不判断真实进展。"],
            risks=risks,
            recommended_next_actions=actions,
            snapshot=current,
        )

    real_progress: list[ProgressClaim] = []
    weak_signals: list[str] = []
    risks = _snapshot_risks(current)

    new_commits = _new_commits(current, baseline)
    if new_commits:
        subjects = "；".join(commit.subject for commit in new_commits[:3])
        real_progress.append(ProgressClaim(
            summary=f"新增 {len(new_commits)} 个提交：{subjects}",
            evidence_refs=[f"git:{commit.sha}" for commit in new_commits],
        ))

    changed_results = changed_artifacts(current.result_files, baseline.result_files)
    if changed_results:
        names = "、".join(item.path for item in changed_results[:4])
        real_progress.append(ProgressClaim(
            summary=f"新增或更新 {len(changed_results)} 个研究产物：{names}",
            evidence_refs=[f"artifact:{item.path}" for item in changed_results],
        ))

    changed_reports = changed_artifacts(current.report_files, baseline.report_files)
    if changed_reports:
        weak_signals.extend(summarize_report(current.path, report) for report in changed_reports[:5])

    baseline_test = baseline.test_result.status
    current_test = current.test_result
    if current_test.status == "passed" and baseline_test != "passed":
        real_progress.append(ProgressClaim(
            summary=f"测试命令已通过：{current_test.command}",
            evidence_refs=[f"test:{current_test.command}"],
        ))
    elif current_test.status == "passed" and (new_commits or changed_results):
        weak_signals.append(f"本周期变更已通过测试命令验证：{current_test.command}")

    if current.dirty_files and not new_commits:
        weak_signals.append("检测到未提交代码活动，但尚不能作为已完成进展。")
    if not real_progress and not weak_signals:
        weak_signals.append("相对上一基线未检测到可归因的新提交、研究产物或报告变化。")

    actions = _recommended_actions(current, real_progress, weak_signals, risks)
    evidence_refs = _dedupe(ref for claim in real_progress for ref in claim.evidence_refs)
    return ProgressAuditReport(
        project_id=current.project_id,
        period=f"{baseline.captured_at.date().isoformat()} 至 {current.captured_at.date().isoformat()}",
        captured_at=current.captured_at,
        baseline_status="compared",
        real_progress=real_progress,
        weak_signals=weak_signals,
        risks=risks,
        recommended_next_actions=actions,
        evidence_refs=evidence_refs,
        snapshot=current,
    )


def _new_commits(current: ProjectSnapshot, baseline: ProjectSnapshot) -> list:
    if not current.git_head or current.git_head == baseline.git_head:
        return []
    commits = []
    for commit in current.recent_commits:
        if commit.sha == baseline.git_head:
            break
        commits.append(commit)
    return commits


def _snapshot_risks(snapshot: ProjectSnapshot) -> list[str]:
    risks = list(snapshot.errors)
    if snapshot.dirty_files:
        risks.append(f"Git 工作区存在 {len(snapshot.dirty_files)} 个未提交文件。")
    tests = snapshot.test_result
    if tests.status == "failed":
        risks.append(f"测试命令失败（退出码 {tests.exit_code}）：{tests.command}")
    elif tests.status == "timed_out":
        risks.append(f"测试命令超时：{tests.command}")
    elif tests.status == "error":
        risks.append(f"测试命令无法执行：{tests.command}")
    return _dedupe(risks)


def _recommended_actions(
    snapshot: ProjectSnapshot,
    real_progress: list[ProgressClaim],
    weak_signals: list[str],
    risks: list[str],
) -> list[str]:
    actions = []
    if snapshot.test_result.status in {"failed", "timed_out", "error"}:
        actions.append("修复或重新配置测试命令，并在下次审计前获得可复现的通过结果。")
    if snapshot.dirty_files:
        actions.append("审阅未提交文件，将完成的工作拆分为可解释的提交。")
    if weak_signals and not real_progress:
        actions.append("把当前活动转化为带测试、提交或研究产物的可验证成果。")
    if real_progress:
        actions.append("为已验证进展补充简短结论，并纳入下一份周报。")
    if not actions:
        actions.append("继续当前研究周期，并在产生新提交或实验产物后重新审计。")
    return _dedupe(actions)


def _project_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "local-project"


def _dedupe(values) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
