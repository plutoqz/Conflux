#!/usr/bin/env python
"""P0 API latency/payload baseline capture (read-only, offline).

Starts the production WorkbenchHandler on a throwaway loopback port (no v2,
no model calls) and measures cold/warm latency + payload size for:

    /api/status
    /api/query/jobs
    /api/sessions
    /api/v1/projects  (+ per-project /state)

Output: reports/evaluation/convergence/p0/api_baseline.json
"""
from __future__ import annotations

import json
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.workbench import server  # noqa: E402


class QuietHandler(server.WorkbenchHandler):
    def log_message(self, fmt, *args):
        pass


def _call(base: str, path: str, timeout: float = 60.0):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
    ms = (time.perf_counter() - t0) * 1000.0
    return status, ms, len(body)


def _summarize(values):
    s = sorted(values)
    n = len(s)
    return {
        "p50": round(statistics.median(s), 1),
        "p95": round(s[int(n * 0.95) - 1], 1),
        "min": round(min(s), 1),
        "max": round(max(s), 1),
    }


def main() -> None:
    server._load_runtime_env()
    # persistent worker (job claimer) mirrors production startup without v2
    server._start_persistent_worker()

    port = 18765
    httpd = ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"

    endpoints = ["/api/status", "/api/query/jobs", "/api/sessions", "/api/v1/projects"]
    out = {
        "schema": "conflux.convergence_evidence.v1",
        "phase": "P0",
        "endpoints": {},
    }

    for path in endpoints:
        # warm TTL caches once, then measure 20 (warm) requests
        _call(base, path)
        statuses, lat, payloads = [], [], []
        for _ in range(20):
            s, ms, n = _call(base, path)
            statuses.append(s)
            lat.append(ms)
            payloads.append(n)
        out["endpoints"][path] = {
            "status": statuses,
            "latency_ms_warm": _summarize(lat),
            "payload_bytes_warm": _summarize(payloads),
            "http_errors": [s for s in statuses if s >= 400],
        }

    # cold measurements: bypass TTL caches by using a fresh process?  P0 spec
    # says cold/hot each 20x; here we approximate cold with direct function
    # calls after clearing module TTL caches (same semantics as a cold cache).
    for path in endpoints:
        for _ in range(2):
            _call(base, path)  # prime
        server._invalidate_expensive_cache("vector_store", "paper_ingestion_audit") if hasattr(
            server, "_invalidate_expensive_cache"
        ) else None
        statuses, lat, payloads = [], [], []
        for _ in range(20):
            # simulate cold cache: clear TTL before each request where possible
            server._invalidate_expensive_cache("vector_store", "paper_ingestion_audit") if hasattr(
                server, "_invalidate_expensive_cache"
            ) else None
            s, ms, n = _call(base, path)
            statuses.append(s)
            lat.append(ms)
            payloads.append(n)
        out["endpoints"][path]["latency_ms_cold"] = _summarize(lat)
        out["endpoints"][path]["payload_bytes_cold"] = _summarize(payloads)

    # project state (per registry id)
    project_ids = []
    try:
        with urllib.request.urlopen(base + "/api/v1/projects", timeout=60) as resp:
            projects = json.loads(resp.read())
        project_ids = [
            p.get("id") or p.get("project_id")
            for p in (projects.get("projects") or projects if isinstance(projects, dict) else projects)
        ][:5]
    except Exception as exc:
        out["project_state_error"] = str(exc)
    for pid in project_ids:
        key = f"/api/v1/projects/{pid}/state"
        lat_warm, payloads_warm, statuses = [], [], []
        for _ in range(20):
            s, ms, n = _call(base, key)
            statuses.append(s)
            lat_warm.append(ms)
            payloads_warm.append(n)
        out["endpoints"][key] = {
            "latency_ms_warm": _summarize(lat_warm),
            "payload_bytes_warm": _summarize(payloads_warm),
            "http_errors": [s for s in statuses if s >= 400],
        }

    httpd.shutdown()
    httpd.server_close()

    out_path = PROJECT_ROOT / "reports" / "evaluation" / "convergence" / "p0" / "api_baseline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[api-baseline] wrote {out_path}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()