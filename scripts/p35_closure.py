"""P3.5 closure runner — cycle audit + confirmed summary for ONE project.

Generic over any registered project (no project-specific hardcoding): refresh
local observations, build the snapshot-comparator draft, confirm the cycle
summary (which becomes the next audit's baseline) and export Markdown/JSON
artifacts next to the legacy progress outputs.

Usage:
    python scripts/p35_closure.py <project_id> [--baseline-revision N]
        [--out reports/evaluation/p3]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux import config  # noqa: E402
from conflux.adapters.sqlite_store import SQLiteDatabase  # noqa: E402
from conflux.core.runtime_home import database_path  # noqa: E402
from conflux.project_registry import ProjectRegistry  # noqa: E402
from conflux.projects import (  # noqa: E402
    ProjectIntelligence,
    SnapshotTrigger,
    build_cycle_audit,
    build_snapshot,
    collect_all_events,
    ingest_events,
    latest_confirmed_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--baseline-revision", type=int, default=None,
                        help="显式指定基线快照修订；缺省取最近已确认摘要")
    parser.add_argument("--confirm", action="store_true",
                        help="确认摘要并写入新基线（不指定则只生成草稿）")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p3"))
    args = parser.parse_args()

    registry = ProjectRegistry(str(PROJECT_ROOT / "projects"), base_dir=PROJECT_ROOT)
    project = registry.get(args.project_id)
    if project is None:
        print(f"[p35] 项目未找到：{args.project_id}")
        return 1

    db_path = database_path()
    intelligence = ProjectIntelligence(SQLiteDatabase(db_path).connect())
    intelligence.ensure_schema()
    try:
        # 1) Local observation refresh (no remote, no model), then compare.
        events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
        added = ingest_events(intelligence, events)
        if added or intelligence.snapshots.latest(project.id) is None:
            build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

        draft = build_cycle_audit(
            intelligence,
            project,
            baseline_revision=args.baseline_revision,
            legacy_out_dir=PROJECT_ROOT / "reports" / "workbench" / "progress" / project.id,
        )
        if not draft.get("ok"):
            print(f"[p35] {draft.get('error')}")
            return 2

        # 2) Optional confirmation -> new baseline + Markdown/JSON artifacts.
        confirmed = None
        if args.confirm:
            from conflux.projects import confirm_cycle_summary

            confirmed = confirm_cycle_summary(
                intelligence,
                project,
                baseline_revision=args.baseline_revision,
                out_dir=PROJECT_ROOT / "reports" / "workbench" / "progress",
            )
            if not confirmed.get("ok"):
                print(f"[p35] 确认失败：{confirmed.get('error')}")
                return 3

        # 3) Persist the closure evidence report.
        out_dir = Path(args.out) / "closure"
        out_dir.mkdir(parents=True, exist_ok=True)
        stored = latest_confirmed_summary(intelligence, project.id)
        report = {
            "project_id": project.id,
            "snapshot": draft["current"],
            "baseline": draft["baseline"],
            "baseline_status": draft["baseline_status"],
            "real_progress": draft["real_progress"],
            "failed_experiments": draft["failed_experiments"],
            "paper_changes": draft["paper_changes"],
            "query_changes": draft["query_changes"],
            "acceptance_updates": draft["acceptance_updates"],
            "risks": draft["risks"],
            "next_cycle_candidates": draft["next_cycle_candidates"],
            "evidence_refs": draft["evidence_refs"],
            "events_added": added,
            "confirmed_summary_id": (confirmed or {}).get("summary_id") or
                                    (stored or {}).get("summary_id", ""),
            "artifacts": (confirmed or {}).get("artifacts", {}),
        }
        report_path = out_dir / f"p35_{project.id}_{int(time.time()) % 100000}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[p35] {project.id}: 基线 {draft['baseline_status']} "
              f"v{draft['baseline']['revision']} → v{draft['current']['revision']}，"
              f"真实进展 {len(draft['real_progress'])} 项，失败实验 {len(draft['failed_experiments'])} 项，"
              f"证据 {len(draft['evidence_refs'])} 条")
        if confirmed:
            print(f"[p35] 已确认：{confirmed['summary_id']}（新基线 v{draft['current']['revision']}）")
            print(f"[p35] 导出：{confirmed['artifacts'].get('markdown_path')} / "
                  f"{confirmed['artifacts'].get('json_path')}")
        print(f"[p35] 报告：{report_path}")
        return 0
    finally:
        intelligence.db.close()


if __name__ == "__main__":
    sys.exit(main())
