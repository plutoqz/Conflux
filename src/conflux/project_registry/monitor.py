"""Read-only monitoring for registered code and research directories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from conflux.progress_audit.artifact_inspector import inspect_artifacts
from conflux.progress_audit.git_inspector import GitInspection, inspect_git

from .models import ProjectDefinition
from .plan_analyzer import discover_plan_documents, public_document_context


DOCUMENT_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx", ".csv", ".tsv", ".json", ".yaml", ".yml"}
IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def monitor_project(
    project: ProjectDefinition,
    *,
    audit_root: str | Path,
    check_remote: bool = False,
) -> dict[str, Any]:
    root = Path(project.path).expanduser().resolve()
    refreshed_at = datetime.now(timezone.utc).isoformat()
    if not root.is_dir():
        return {
            "project": project.to_dict(),
            "path_exists": False,
            "health": "error",
            "refreshed_at": refreshed_at,
            "repository": GitInspection(checked_at=refreshed_at).to_dict(),
            "documents": _empty_file_summary(),
            "results": _empty_file_summary(),
            "reports": _empty_file_summary(),
            "latest_audit": None,
            "alerts": [{
                "severity": "error",
                "title": "项目路径不可用",
                "detail": f"本地目录不存在或无法访问：{root}",
            }],
        }

    git = inspect_git(root, check_remote=check_remote)
    documents = _inspect_documents(root, project)
    result_records, report_records = inspect_artifacts(
        root,
        result_dirs=project.result_dirs,
        report_dirs=project.report_dirs,
        max_files=5000,
    )
    results = _records_summary(result_records)
    reports = _records_summary(record for record in report_records if _is_meaningful_report(record.path))
    latest_audit = _load_latest_audit(Path(audit_root) / project.id / "progress_audit.json")
    plan_context = public_document_context(discover_plan_documents(project, max_files=24))
    alerts = _build_alerts(project, git, latest_audit)
    if (plan_context.get("charter") or {}).get("status") == "missing":
        alerts.append({
            "severity": "warning",
            "title": "缺少项目纲领",
            "detail": "只读监控仍可使用，但智能计划分析的依据不足。可生成 PROJECT.md 草案后人工确认。",
        })
    health = _health_from_alerts(alerts)
    return {
        "project": project.to_dict(),
        "path_exists": True,
        "health": health,
        "refreshed_at": refreshed_at,
        "repository": git.to_dict(),
        "documents": documents,
        "results": results,
        "reports": reports,
        "latest_audit": latest_audit,
        "plan_context": plan_context,
        "alerts": alerts,
    }


def _inspect_documents(root: Path, project: ProjectDefinition) -> dict[str, Any]:
    paths: dict[str, Path] = {}
    for raw in project.document_files:
        path = (root / raw).resolve()
        if _within(path, root) and path.is_file():
            paths[path.relative_to(root).as_posix()] = path
    for raw_dir in project.document_dirs:
        directory = (root / raw_dir).resolve()
        if not _within(directory, root) or not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if len(paths) >= 1000:
                break
            if (
                path.is_file()
                and path.suffix.casefold() in DOCUMENT_EXTENSIONS
                and not any(part in IGNORED_PARTS for part in path.parts)
            ):
                paths[path.relative_to(root).as_posix()] = path
    return _path_summary(paths)


def _path_summary(paths: dict[str, Path]) -> dict[str, Any]:
    records = []
    total_size = 0
    for relative, path in paths.items():
        try:
            stat = path.stat()
        except OSError:
            continue
        total_size += stat.st_size
        records.append({
            "path": relative,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })
    records.sort(key=lambda item: item["modified_at"], reverse=True)
    return {
        "count": len(records),
        "size_bytes": total_size,
        "latest_modified_at": records[0]["modified_at"] if records else "",
        "recent_files": records[:5],
    }


def _records_summary(records: Iterable[Any]) -> dict[str, Any]:
    values = sorted(records, key=lambda item: item.modified_at, reverse=True)
    return {
        "count": len(values),
        "size_bytes": sum(item.size_bytes for item in values),
        "latest_modified_at": values[0].modified_at if values else "",
        "recent_files": [
            {
                "path": item.path,
                "size_bytes": item.size_bytes,
                "modified_at": item.modified_at,
            }
            for item in values[:5]
        ],
    }


def _is_meaningful_report(path: str) -> bool:
    normalized = str(path or "").replace("\\", "/").casefold()
    parts = normalized.split("/")
    name = parts[-1] if parts else normalized
    if not name.endswith((".md", ".markdown")):
        return False
    if name.endswith((".draft.md", ".verified.md", ".audit.md", ".sources.md", ".diagnostic.md")):
        return False
    if any(part.startswith(("test", "eval", "live-quality")) for part in parts):
        return False
    if "workbench" in parts and "query" not in parts:
        return False
    return True


def _empty_file_summary() -> dict[str, Any]:
    return {"count": 0, "size_bytes": 0, "latest_modified_at": "", "recent_files": []}


def _load_latest_audit(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    snapshot = payload.get("snapshot") or {}
    test = snapshot.get("test_result") or {}
    return {
        "captured_at": payload.get("captured_at") or "",
        "period": payload.get("period") or "",
        "baseline_status": payload.get("baseline_status") or "",
        "real_progress": payload.get("real_progress") or [],
        "weak_signals": payload.get("weak_signals") or [],
        "risks": payload.get("risks") or [],
        "recommended_next_actions": payload.get("recommended_next_actions") or [],
        "test_status": test.get("status") or "not_run",
        "artifact_count": len(snapshot.get("result_files") or []),
        "report_count": len(snapshot.get("report_files") or []),
    }


def _build_alerts(
    project: ProjectDefinition,
    git: GitInspection,
    latest_audit: dict[str, Any] | None,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for error in git.errors:
        alerts.append({"severity": "error", "title": "Git 状态读取失败", "detail": error})
    if git.is_repository:
        if git.dirty_files:
            alerts.append({
                "severity": "warning",
                "title": "存在未提交变更",
                "detail": f"本地工作区有 {len(git.dirty_files)} 个未提交文件。",
            })
        if git.sync_status == "behind":
            alerts.append({
                "severity": "warning",
                "title": "本地版本落后",
                "detail": f"当前分支比远程落后 {git.behind} 个提交。监控不会自动拉取。",
            })
        elif git.sync_status == "diverged":
            alerts.append({
                "severity": "error",
                "title": "本地与远程已分叉",
                "detail": f"本地领先 {git.ahead}、落后 {git.behind} 个提交，请人工确认同步策略。",
            })
        elif git.sync_status == "ahead":
            alerts.append({
                "severity": "info",
                "title": "本地有未推送版本",
                "detail": f"当前分支领先远程 {git.ahead} 个提交。监控不会自动推送。",
            })
        for warning in git.warnings:
            alerts.append({"severity": "warning", "title": "远程版本需要确认", "detail": warning})
    if not project.plan.overall_goal:
        alerts.append({
            "severity": "warning",
            "title": "总体目标尚未定义",
            "detail": "请在项目配置中填写权威目标，或从项目文档提取候选项后确认。",
        })
    if latest_audit is None:
        alerts.append({
            "severity": "info",
            "title": "尚未建立进度基线",
            "detail": "运行一次进度审计后，面板才能比较计划与实际证据。",
        })
    else:
        risks = latest_audit.get("risks") or []
        if risks:
            alerts.append({
                "severity": "warning",
                "title": "最近审计存在风险",
                "detail": f"最近一次审计记录了 {len(risks)} 项风险。",
            })
    return alerts


def _health_from_alerts(alerts: list[dict[str, str]]) -> str:
    severities = {item.get("severity") for item in alerts}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warning"
    if "info" in severities:
        return "info"
    return "ok"


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
