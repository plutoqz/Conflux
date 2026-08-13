"""P3.3 performance baseline — measure the snapshot-driven v1 project API.

Timings are collected over HTTP against a running Workbench so they include
the full request path (server, SQLite reads, JSON serialization).  The
legacy `/api/projects` path is measured as a contrast reference
(plan §13.1 targets: cached state API P95 <= 300 ms, first-screen proxy
<= 800 ms = status + list + state P95 sum).

Usage:
    python scripts/bench_p3_overview.py [--base http://127.0.0.1:8765]
        [--iterations 30] [--out reports/evaluation/p3/p33_perf_baseline.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

V1_ENDPOINTS = {
    "GET /api/v1/projects": "/api/v1/projects",
    "GET /api/v1/projects/{id}/state": "/api/v1/projects/{id}/state",
    "GET /api/v1/projects/{id}/documents": "/api/v1/projects/{id}/documents",
    "GET /api/v1/projects/{id}/reviews": "/api/v1/projects/{id}/reviews",
    "GET /api/v1/projects/{id}/activity": "/api/v1/projects/{id}/activity",
    "GET /api/v1/projects/{id}/work-items": "/api/v1/projects/{id}/work-items",
}
LEGACY_ENDPOINTS = {
    "GET /api/projects (legacy scan)": "/api/projects",
    "GET /api/status": "/api/status",
}


def _request(base: str, path: str) -> tuple[float, int]:
    started = time.perf_counter()
    with urllib.request.urlopen(base + path, timeout=30) as response:
        body = response.read()
    return (time.perf_counter() - started) * 1000, len(body)


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(pct / 100 * (len(ordered) - 1)))))
    return ordered[index]


def _report_row(name: str, samples: list[float], bytes_samples: list[int]) -> dict:
    return {
        "endpoint": name,
        "count": len(samples),
        "p50_ms": round(statistics.median(samples), 1),
        "p95_ms": round(_percentile(samples, 95), 1),
        "max_ms": round(max(samples), 1),
        "mean_ms": round(statistics.mean(samples), 1),
        "payload_kb": round(statistics.median(bytes_samples) / 1024, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p3" / "p33_perf_baseline.json"))
    args = parser.parse_args()

    # Pick the first registered project with a snapshot.
    with urllib.request.urlopen(args.base + "/api/v1/projects", timeout=30) as response:
        listing = json.loads(response.read().decode("utf-8"))
    projects = listing.get("projects") or []
    if not projects:
        print("[bench] no registered projects found; is the Workbench running?")
        return 1
    target = next((item for item in projects if item.get("revision")), projects[0])
    project_id = target["id"]
    print(f"[bench] project={project_id} revision={target['revision']} docs={target['documents_total']}")

    rows: list[dict] = []
    print("[bench] warmup + measure v1 endpoints")
    for name, path in V1_ENDPOINTS.items():
        resolved = path.replace("{id}", project_id)
        for _ in range(3):  # warmup
            _request(args.base, resolved)
        samples: list[float] = []
        sizes: list[int] = []
        for _ in range(args.iterations):
            elapsed, size = _request(args.base, resolved)
            samples.append(elapsed)
            sizes.append(size)
        row = _report_row(name, samples, sizes)
        rows.append(row)
        print(f"[bench] {name}: p50={row['p50_ms']}ms p95={row['p95_ms']}ms payload={row['payload_kb']}KB")

    print("[bench] contrast: legacy paths (3 iterations)")
    for name, path in LEGACY_ENDPOINTS.items():
        samples = []
        sizes = []
        for _ in range(3):
            elapsed, size = _request(args.base, path)
            samples.append(elapsed)
            sizes.append(size)
        row = _report_row(name, samples, sizes)
        rows.append(row)
        print(f"[bench] {name}: p50={row['p50_ms']}ms p95={row['p95_ms']}ms payload={row['payload_kb']}KB")

    state_row = next(row for row in rows if row["endpoint"].endswith("/state"))
    list_row = next(row for row in rows if row["endpoint"] == "GET /api/v1/projects")
    status_row = next(row for row in rows if row["endpoint"] == "GET /api/status")
    first_screen_proxy = round(state_row["p95_ms"] + list_row["p95_ms"] + status_row["p95_ms"], 1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base": args.base,
        "project_id": project_id,
        "snapshot_revision": target["revision"],
        "iterations": args.iterations,
        "targets": {
            "state_api_p95_ms": 300,
            "first_screen_proxy_p95_ms": 800,
        },
        "rows": rows,
        "first_screen_proxy_ms": first_screen_proxy,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown = [
        f"# P3.3 项目页性能基线（{report['collected_at']}）",
        "",
        f"- 服务：{args.base}，测量项目：`{project_id}`（快照 v{target['revision']}，{target['documents_total']} 份文档）",
        f"- 每端点 {args.iterations} 次请求（预热 3 次）；旧路径对照 3 次",
        "",
        "| 端点 | P50 | P95 | Max | 平均 | 载荷 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        markdown.append(
            f"| {row['endpoint']} | {row['p50_ms']} ms | {row['p95_ms']} ms | "
            f"{row['max_ms']} ms | {row['mean_ms']} ms | {row['payload_kb']} KB |"
        )
    markdown += [
        "",
        f"首屏代理（status + 列表 + state 三项 P95 之和）：**{first_screen_proxy} ms**（目标 ≤800 ms）",
        f"已缓存项目状态 API P95 目标：≤300 ms（见 `/state` 行）",
        "",
        "> 代理口径说明：真实首屏还包括浏览器渲染与 SSE 建连，需真机驱动复测；",
        "> 页面 GET 路径零模型/远程调用的保证由 `tests/test_p3_workbench.py` 的 monitor_project 守卫断言覆盖。",
        "> `/api/status` 的 Chroma 审计子查询带 30 秒 TTL 缓存：冷启动后的第一次请求仍约为 1.5–2 s，",
        "> 之后 30 秒窗口内所有刷新均命中缓存（上表为该稳定态）；变更类操作（入库/重建/删除索引）会主动失效缓存。",
        "",
    ]
    md_path = out.with_suffix(".md")
    md_path.write_text("\n".join(markdown), encoding="utf-8")
    print(f"[bench] wrote {out} and {md_path}")
    print(f"[bench] first-screen proxy P95: {first_screen_proxy} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
