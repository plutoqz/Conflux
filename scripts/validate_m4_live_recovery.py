"""Controlled live validation for durable Workbench query recovery."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository  # noqa: E402
from conflux.adapters.sqlite_store import EventStore, JobQueue, SQLiteDatabase  # noqa: E402
from conflux.workbench.jobs import JobManager  # noqa: E402


def _load_runtime_env() -> None:
    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.workbench", override=False)


def _child(db_path: Path, run_file: Path, query: str) -> int:
    _load_runtime_env()
    manager = JobManager(db_path=db_path, start_worker=True, poll_interval=0.1, lease_seconds=6.0)
    submitted = manager.submit(query, {"depth": "quick", "output_dir": str(db_path.parent / "reports")})
    run_file.write_text(submitted["run_id"], encoding="utf-8")
    deadline = time.time() + 45
    while time.time() < deadline:
        status = manager.get(submitted["run_id"]) or {}
        if status.get("status") == "running":
            time.sleep(8)
            os._exit(99)
        time.sleep(0.2)
    return 2


def _validate(output_dir: Path, query: str) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "conflux.db"
    run_file = output_dir / "run_id.txt"
    command = [sys.executable, str(Path(__file__).resolve()), "--child", "--output-dir", str(output_dir), "--query", query]
    started = time.time()
    child = subprocess.run(command, cwd=ROOT, timeout=90)
    if child.returncode != 99 or not run_file.exists():
        raise RuntimeError(f"crash worker did not exit at the intended point: {child.returncode}")
    run_id = run_file.read_text(encoding="utf-8").strip()
    _load_runtime_env()
    manager = JobManager(db_path=db_path, start_worker=True, poll_interval=0.1, lease_seconds=6.0)
    deadline = time.time() + 420
    terminal = {}
    while time.time() < deadline:
        terminal = manager.get(run_id) or {}
        if terminal.get("status") not in {"pending", "running"}:
            break
        time.sleep(0.5)
    db = SQLiteDatabase(db_path).connect()
    db.bootstrap_schema()
    try:
        events = EventStore(db).list(run_id=run_id, limit=1000)
        queued = JobQueue(db).get(run_id) or {}
        ledger = EvidenceLedgerRepository(db).run_ledger(run_id)
    finally:
        db.close()
    result = {
        "schema_version": "conflux-m4-live-recovery-v1",
        "run_id": run_id,
        "query": query,
        "child_exit_code": child.returncode,
        "terminal_status": terminal.get("status"),
        "queue_status": queued.get("status"),
        "resume_event_count": sum(1 for item in events if item.get("stage") == "job_resume"),
        "event_count": len(events),
        "ledger_evidence_count": len(ledger["evidence"]),
        "ledger_claim_count": len(ledger["claims"]),
        "elapsed_seconds": round(time.time() - started, 3),
        "live_external": True,
        "passed": bool(
            child.returncode == 99
            and terminal.get("status") in {"completed", "completed_with_warnings", "completed_diagnostic"}
            and queued.get("status") == "completed"
            and any(item.get("stage") == "job_resume" for item in events)
            and len(ledger["evidence"]) > 0
        ),
    }
    (output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--output-dir", default="reports/evaluation/m4_live_recovery")
    parser.add_argument("--query", default="What are the core mechanisms and limitations of retrieval-augmented generation?")
    args = parser.parse_args(argv)
    output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    if args.child:
        return _child(output_dir / "conflux.db", output_dir / "run_id.txt", args.query)
    return _validate(output_dir, args.query)


if __name__ == "__main__":
    raise SystemExit(main())
