"""P3.6 performance convergence runner — benchmark, A/B and cost evidence.

Generic over registered projects; the synthetic large-project fixture is
built deterministically (no network, no model).  Measures:

- incremental snapshot build time (event cursor replay, >1000 events),
- materialized page-read paths (projects list / project state / audit),
- legacy aggregation path for the A/B comparison (before its removal),
- model-call cost: page reads must invoke zero model providers.

Usage:
    python scripts/p36_perf.py [project_id] [--out reports/evaluation/p3]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.adapters.sqlite_store import SQLiteDatabase  # noqa: E402
from conflux.projects import (  # noqa: E402
    EventKind,
    ProjectIntelligence,
    SnapshotTrigger,
    build_cycle_audit,
    build_snapshot,
    new_event,
    new_snapshot,
)
from conflux.project_registry.models import Milestone, ProjectDefinition  # noqa: E402


def _p95(values: list[float]) -> float:
    return sorted(values)[int(len(values) * 0.95) - 1] if values else 0.0


def _med(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _sample(fn, rounds: int = 10) -> tuple[float, float]:
    values = []
    for _ in range(rounds):
        started = time.perf_counter()
        fn()
        values.append((time.perf_counter() - started) * 1000)
    return _med(values), _p95(values)


def _synthetic_project() -> ProjectDefinition:
    project = ProjectDefinition(id="perf-fixture", name="Perf fixture", path=".")
    project.plan.overall_goal = "Perf fixture goal"
    project.plan.milestones = [
        Milestone(id=f"m{i}", title=f"Milestone {i}", status="in_progress",
                  deliverables=[f"run-{i}.csv"]) for i in range(40)
    ]
    project.plan.next_actions = [f"action {i}" for i in range(40)]
    return project


def benchmark_synthetic() -> dict:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db = SQLiteDatabase(str(Path(tmp) / "perf.db")).connect()
        db.bootstrap_schema()
        intelligence = ProjectIntelligence(db)
        intelligence.ensure_schema()
        project = _synthetic_project()

        # First build (full replay baseline).
        first_med, first_p95 = _sample(
            lambda: build_snapshot(intelligence, project), rounds=5
        )
        # Ingest 1500 events: 1200 runs + 300 document events.
        started = time.perf_counter()
        for index in range(1200):
            intelligence.events.append(new_event(
                project.id, EventKind.RESEARCH_QUERY_COMPLETED,
                payload={"run_id": f"run-{index:04d}", "status": "completed",
                         "work_item_id": "", "elapsed_seconds": 1.0},
            ))
        for index in range(300):
            intelligence.events.append(new_event(
                project.id, EventKind.DOCUMENT_CHANGED,
                payload={"path": f"docs/d{index}.md", "index_version": f"v{index // 100}"},
            ))
        ingest_ms = (time.perf_counter() - started) * 1000

        full_med, full_p95 = _sample(
            lambda: build_snapshot(intelligence, project), rounds=3
        )
        # Incremental: one new event per build.
        def incremental_build():
            intelligence.events.append(new_event(
                project.id, EventKind.GIT_HEAD_CHANGED,
                payload={"root": ".", "branch": "main", "head": f"h{int(time.time() * 1000)}",
                         "recent_subjects": ["x"], "checked_at": time.time()},
            ))
            return build_snapshot(intelligence, project, trigger=SnapshotTrigger.SCHEDULED)

        inc_med, inc_p95 = _sample(incremental_build, rounds=10)

        latest = intelligence.snapshots.latest(project.id)
        snapshot_kb = len(json.dumps(latest.model_dump()).encode("utf-8")) / 1024

        def read_audit():
            return build_cycle_audit(intelligence, project, baseline_revision=latest.revision - 1)

        audit_med, audit_p95 = _sample(read_audit, rounds=5)

        # Scaling: incremental build must stay flat as the event log grows
        # (cursor replay applies only new events).  Bulk-ingest in one
        # transaction so fixture setup stays fast.
        scaling = []
        for total in (3000, 10000, 20000):
            connection = intelligence.db.connection
            connection.execute("BEGIN")
            for index in range(total - 1500):
                connection.execute(
                    "INSERT INTO project_events (project_id, kind, payload_json, created_at, dedup_key)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (project.id, "document.changed",
                     '{"path": "docs/scale.md", "index_version": "v9"}',
                     time.time(), f"scale-{total}-{index}"),
                )
            connection.commit()
            inc_med, inc_p95 = _sample(incremental_build, rounds=5)
            scaling.append({
                "total_events": total,
                "incremental_build_ms": {"med": round(inc_med, 1), "p95": round(inc_p95, 1)},
            })
        db.close()
    return {
        "first_build_ms": {"med": round(first_med, 1), "p95": round(first_p95, 1)},
        "ingest_1500_events_ms": round(ingest_ms, 1),
        "full_replay_build_ms": {"med": round(full_med, 1), "p95": round(full_p95, 1)},
        "incremental_build_ms": {"med": round(inc_med, 1), "p95": round(inc_p95, 1)},
        "snapshot_kb": round(snapshot_kb, 1),
        "event_count": 1500,
        "audit_read_ms": {"med": round(audit_med, 1), "p95": round(audit_p95, 1)},
        "scaling": scaling,
    }


class _ModelCallCounter:
    """Instrumentation: prove zero model calls during measured reads."""

    def __init__(self) -> None:
        self.calls = 0

    def install(self) -> None:
        import conflux.model_factory as factory

        original = factory.create_chat_model

        def counting(*args, **kwargs):
            self.calls += 1
            return original(*args, **kwargs)

        factory.create_chat_model = counting
        self._restore = lambda: setattr(factory, "create_chat_model", original)

    def restore(self) -> None:
        self._restore()


def benchmark_real(project_id: str) -> dict:
    from conflux.workbench import server

    counter = _ModelCallCounter()
    counter.install()
    try:
        list_med, list_p95 = _sample(server.build_p3_projects, rounds=10)
        state_med, state_p95 = _sample(
            lambda: server.build_p3_project_state(project_id), rounds=10
        )
        audit_med, audit_p95 = _sample(
            lambda: server.build_p3_audit(project_id), rounds=5
        )
        model_calls = counter.calls
        # Legacy aggregation (A/B baseline; measured before removal).
        legacy_med, legacy_p95 = (0.0, 0.0)
        if hasattr(server, "build_projects_overview"):
            legacy_med, legacy_p95 = _sample(server.build_projects_overview, rounds=3)
    finally:
        counter.restore()
    return {
        "projects_list_ms": {"med": round(list_med, 1), "p95": round(list_p95, 1)},
        "project_state_ms": {"med": round(state_med, 1), "p95": round(state_p95, 1)},
        "audit_read_ms": {"med": round(audit_med, 1), "p95": round(audit_p95, 1)},
        "legacy_overview_ms": {"med": round(legacy_med, 1), "p95": round(legacy_p95, 1)},
        "model_calls_during_reads": model_calls,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", nargs="?", default="conflux")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p3"))
    args = parser.parse_args()

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "synthetic": benchmark_synthetic(),
        "real": benchmark_real(args.project_id),
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "p36_perf_baseline.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[p36] 报告：{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
