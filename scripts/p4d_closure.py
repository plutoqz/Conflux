"""P4.3 D closure runner — experiment registry + mentor weekly report闭环.

Generic over any registered project (no project-specific hardcoding).  The
runner drives the D acceptance chain end-to-end against the *runtime* DB:

    登记实验(CLI 服务路径) → 周期审计 diff（实验成为真实进展/失败项）
    → 周报数据块（确定性） → LLM 组织（缺模型时确定性回退）
    → 校验（数字/哈希可回溯） → 导出 Markdown/JSON

Assertions encode D2（数字可追溯）/D3（全链路闭环）/D4（模型不可编造）;
a failure exits non-zero so the closure report stays honest.

Usage:
    python scripts/p4_d_closure.py <project_id> [--register-demo] [--out reports/evaluation/p4]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.adapters.sqlite_store import SQLiteDatabase  # noqa: E402
from conflux.core.runtime_home import database_path  # noqa: E402
from conflux.mentor_report import (  # noqa: E402
    build_mentor_report,
    export_mentor_report_markdown,
    generate_mentor_report,
    validate_report_text,
)  # noqa: E402
from conflux.project_registry import ProjectRegistry  # noqa: E402
from conflux.projects import (  # noqa: E402
    ProjectIntelligence,
    SnapshotTrigger,
    build_cycle_audit,
    build_snapshot,
    collect_all_events,
    ingest_events,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--register-demo", action="store_true",
                        help="先登记两个演示实验（幂等），用于全链路演示")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p4"))
    args = parser.parse_args()

    registry = ProjectRegistry(PROJECT_ROOT / "projects", base_dir=PROJECT_ROOT)
    project = registry.get(args.project_id)
    if project is None:
        print(f"[p4d] 项目未找到：{args.project_id}")
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    intelligence = ProjectIntelligence(db)
    intelligence.ensure_schema()

    steps: list[dict[str, Any]] = []
    failures: list[str] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        steps.append({"name": name, "ok": ok, "detail": detail, "at": time.time()})
        print(f"[p4d] {'PASS' if ok else 'FAIL'} {name} {detail}")
        if not ok:
            failures.append(f"{name}: {detail}")

    try:
        # 0) Local observation refresh (no remote, no model).
        events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
        added = ingest_events(intelligence, events)
        if added or intelligence.snapshots.latest(project.id) is None:
            build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)

        # 0.5) Ensure a confirmed baseline exists so the experiment period
        #      window (baseline.created_at, current.created_at] is non-empty.
        from conflux.projects import confirm_cycle_summary, latest_confirmed_summary

        if latest_confirmed_summary(intelligence, project.id) is None:
            baseline_result = confirm_cycle_summary(intelligence, project)
            if not baseline_result.get("ok"):
                print(f"[p4d] 基线确认失败：{baseline_result.get('error')}")
                return 1
            print("[p4d] 已确认首个周期基线（新基线就绪）")

        if args.register_demo:
            from conflux.experiments import ExperimentRepository

            repo = ExperimentRepository(intelligence.db)
            stamp = int(time.time()) % 10000
            demo_entries = [
                dict(
                    project_id=project.id,
                    name="p4d-demo",
                    hypothesis="闭环演示：登记即进审计",
                    params={"lr": 1e-3, "bs": 32},
                    metrics={"acc": 0.912, "loss": 0.21},
                    status="done",
                    commit_hash="a" * 40,
                    source_ref="closure:demo-1",
                ),
                dict(
                    project_id=project.id,
                    name="p4d-demo-fail",
                    hypothesis="失败演示",
                    params={"lr": 1e-1},
                    metrics={},
                    status="failed",
                    commit_hash="b" * 40,
                    source_ref="closure:demo-2",
                ),
            ]
            for entry in demo_entries:
                repo.register(**entry)
            # New snapshot => a fresh period with the entries inside it.
            time.sleep(0.05)
            events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
            ingest_events(intelligence, events)
            build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
        experiments = []
        try:
            from conflux.experiments import ExperimentRepository

            repo = ExperimentRepository(intelligence.db)
            experiments = repo.list(project.id)
        except Exception as exc:
            record("D1 实验表可读", False, str(exc))
            experiments = []
        record("D1 实验登记服务", len(experiments) > 0, f"count={len(experiments)}")

        # 2) Build cycle audit draft — completed experiments become claims.
        draft = build_cycle_audit(intelligence, project)
        if not draft.get("ok"):
            print(f"[p4d] 审计草稿失败：{draft.get('error')}")
            return 1
        exp_claims = [c for c in draft.get("real_progress") or []
                      if str(c.get("category") or "") == "experiment"]
        record("D3 实验进入周期审计", len(exp_claims) >= 1,
               f"claims={len(exp_claims)}")

        # 3) Mentor report data block — deterministic, zero model.
        data = build_mentor_report(intelligence, project)
        if not data.get("ok"):
            print(f"[p4d] 周报数据块失败：{data.get('error')}")
            return 1
        block = str(data.get("data_block") or "")
        record("D2 数据块含 exp 引用", "<exp:" in block,
               f"chars={len(block)}")

        # 4) Deterministic fallback composition (no model in CI/offline).
        report, problems = generate_mentor_report(data)
        record("D4 确定性回退无失败", not problems, f"problems={len(problems)}")
        record("D2 报告含数据清单", "数据清单" in report)

        # 5) Validation gate: a fabricated number must be rejected (D4).
        forged = report + "\n本周完成 87 项实验，t4stH4sh 提升 42%"
        forged_problems = validate_report_text(forged, data)
        record("D4 未登记数字被拒绝", len(forged_problems) > 0,
               f"rejected={forged_problems[:2]}")

        # 6) Export.
        artifacts = export_mentor_report_markdown(
            data, report, out_dir=out_dir / project.id
        )
        record("D 周报导出", Path(artifacts["markdown_path"]).exists(),
               artifacts["markdown_path"])

    finally:
        db.close()

    payload = {
        "ok": not failures,
        "project_id": project.id,
        "steps": steps,
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    report_path = out_dir / f"p4d_closure_{time.strftime('%Y%m%d')}.json"
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[p4d] 闭环报告：{report_path}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())