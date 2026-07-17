"""Command line interface for local project progress auditing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from conflux.research_profile import load_profile

from .auditor import audit_project, create_project_snapshot
from .progress_report import load_snapshot, write_progress_artifacts, write_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Conflux project progress audit")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "audit"):
        command = subparsers.add_parser(name)
        command.add_argument("--profile", required=True, help="研究画像 YAML 路径")
        command.add_argument("--project", help="覆盖画像中的项目路径")
        command.add_argument("--out-dir", default="reports/progress", help="审计输出目录")
        command.add_argument("--test-command", default="", help="可选测试命令")
        command.add_argument("--test-timeout", type=int, default=120, help="测试超时秒数")
    subparsers.choices["audit"].add_argument("--since", choices=["last"], default="last")
    args = parser.parse_args(argv)

    try:
        profile_path = Path(args.profile)
        profile = load_profile(profile_path)
        projects = [Path(args.project).expanduser().resolve()] if args.project else profile.normalized_project_paths(profile_path.parent)
        if not projects:
            raise ValueError("研究画像没有配置 project_paths，请使用 --project 指定项目路径。")

        summaries = []
        for index, project in enumerate(projects):
            project_id = profile.id if len(projects) == 1 else f"{profile.id}-{index + 1}"
            output = Path(args.out_dir) / project_id
            snapshot_path = output / "project_snapshot.json"
            if args.command == "snapshot":
                snapshot = create_project_snapshot(
                    project,
                    project_id=project_id,
                    test_command=args.test_command or None,
                    test_timeout_seconds=args.test_timeout,
                )
                write_snapshot(snapshot, snapshot_path)
                summaries.append({"project_id": project_id, "snapshot": str(snapshot_path.resolve())})
            else:
                baseline = load_snapshot(snapshot_path)
                report = audit_project(
                    project,
                    baseline=baseline,
                    project_id=project_id,
                    test_command=args.test_command or None,
                    test_timeout_seconds=args.test_timeout,
                )
                artifacts = write_progress_artifacts(report, out_dir=output)
                summaries.append({
                    "project_id": project_id,
                    "baseline_status": report.baseline_status,
                    "markdown": str(artifacts.markdown_path.resolve()),
                    "json": str(artifacts.json_path.resolve()),
                    "snapshot": str(artifacts.snapshot_path.resolve()),
                })
        print(json.dumps(summaries, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2
