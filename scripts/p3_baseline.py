"""P3.0 baseline — measure current project-page response cost.

Runs `build_projects_overview` / `monitor_project` against the registered
projects and records timing + payload sizes, so P3.1's snapshot-backed path
has a comparison baseline (plan §P3.0).

Usage:
    python scripts/p3_baseline.py [--out reports/workbench/p3_baseline.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.project_registry import ProjectRegistry  # noqa: E402
from conflux.project_registry.monitor import monitor_project  # noqa: E402

DEFAULT_PROJECTS_DIR = "projects"
DEFAULT_PROGRESS_DIR = "reports/progress"


def _payload_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-dir", default=str(PROJECT_ROOT / DEFAULT_PROJECTS_DIR))
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "workbench" / "p3_baseline.json"))
    args = parser.parse_args()

    registry = ProjectRegistry(args.registry_dir, base_dir=PROJECT_ROOT)
    loaded = registry.load_all()
    results: list[dict] = []
    for project in loaded.projects:
        started = time.perf_counter()
        overview = monitor_project(
            project,
            audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
            check_remote=False,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        results.append({
            "project_id": project.id,
            "elapsed_ms": elapsed_ms,
            "payload_bytes": _payload_size(overview),
            "path_exists": overview.get("path_exists"),
            "health": overview.get("health"),
        })
        print(f"[baseline] {project.id}: {elapsed_ms} ms, {_payload_size(overview)} bytes")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": time.time(),
        "registry_dir": args.registry_dir,
        "projects": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[baseline] written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
