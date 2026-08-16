#!/usr/bin/env python
"""P1.1 claim/lease timing probe (read-only, offline).

Runs a real subprocess Worker against an isolated temp SQLite DB, waits for the
worker to report ready (import + DB bootstrap done), then submits one quick job
and records submit/claim timing. All timing is monotonic. The window used by the
original recovery test (5s from submit to running) is also reported.

Output: one JSON evidence file per invocation, plus a machine-readable summary
printed to stdout (one JSON line), suitable for `--repeats N` looping.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
WORKER_SCRIPT = str(PROJECT_ROOT / "scripts" / "_p1_worker_probe.py")


def _db_ready(db_path: Path, poll: float = 0.02, timeout: float = 30.0) -> bool:
    """True once the jobs table exists (worker bootstrap visible to others)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            con = sqlite3.connect(str(db_path), timeout=0.5)
            try:
                row = con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'"
                ).fetchone()
                if row:
                    return True
            finally:
                con.close()
        except sqlite3.Error:
            pass
        time.sleep(wait)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iters", type=int, default=15)
    parser.add_argument(
        "--outdir",
        default=str(PROJECT_ROOT / "reports" / "evaluation" / "convergence" / "p1"),
    )
    args = parser.parse_args()

    from conflux.adapters.sqlite_store import JobQueue, SQLiteDatabase
    from conflux.workbench.jobs import JobManager

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    runs = []
    for i in range(args.iters):
        with tempfile.TemporaryDirectory(prefix=f"p1probe_{i}_") as td:
            dbp = Path(td) / "flow.db"
            submitter = JobManager(db_path=dbp, start_worker=False)
            proc = subprocess.Popen(
                [sys.executable, WORKER_SCRIPT, str(dbp)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # 1. Wait for worker ready (DB bootstrap done) — not a blind sleep.
            ready_ok = _db_ready(dbp)
            t_wait_ms = 0.0
            if not ready_ok:
                # fall back to bounded wait; record as failure signal
                time.sleep(1.0)
                t_wait_ms = -1.0  # signal missing ready marker
            else:
                t0 = time.perf_counter()
                # small settle for bootstrap transaction to commit
                # (jobs table visible before bootstrap SQLite tx commits)
                deadline = time.time() + 5.0
                while time.time() < deadline:
                    try:
                        db = SQLiteDatabase(dbp).connect()
                        db.bootstrap_schema()
                        db.close()
                        break
                    except Exception:
                        time.sleep(0.02)
                t_wait_ms = (time.perf_counter() - t0) * 1000.0

            t_start = time.perf_counter()
            rid = submitter.submit("claim timing probe", {"depth": "quick"})["run_id"]
            t_submit_ms = (time.perf_counter() - t_start) * 1000.0

            # 2. Wait for claim (poll DB, not a blind sleep).
            claim_ms = None
            deadline = time.time() + 10.0
            while time.time() < deadline:
                db = SQLiteDatabase(dbp).connect()
                try:
                    queued = JobQueue(db).get(rid)
                finally:
                    db.close()
                if queued and queued["status"] == "running":
                    claim_ms = (time.perf_counter() - t_start) * 1000.0
                    break
                time.sleep(0.01)
            if claim_ms is None:
                claim_ms = -1.0

            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

            record = {
                "iter": i,
                "ready_ok": ready_ok,
                "ready_wait_ms": round(t_wait_ms, 1),
                "submit_ms": round(t_submit_ms, 1),
                "claim_ms": round(claim_ms, 1),
            }
            runs.append(record)

    # Summary
    claims = [r["claim_ms"] for r in runs if r["claim_ms"] >= 0]
    summary = {
        "schema": "conflux.convergence_evidence.v1",
        "phase": "P1.1",
        "kind": "claim_lease_timing_probe",
        "mode": "offline",
        "iters": args.iters,
        "ready_ok": sum(1 for r in runs if r["ready_ok"]),
        "ready_missing": sum(1 for r in runs if not r["ready_ok"]),
        "claim_ok": len(claims),
        "claim_failed": args.iters - len(claims),
        "claim_p50_ms": round(statistics.median(claims), 1) if claims else None,
        "claim_p95_ms": round(sorted(claims)[int(len(claims) * 0.95) - 1], 1) if claims else None,
        "runs": runs,
    }
    outfile = outdir / "p11_claim_lease_probe.json"
    with outfile.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()