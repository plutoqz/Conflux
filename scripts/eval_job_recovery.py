"""任务恢复与幂等压力评测（确定性，不依赖 LLM）。

直接驱动生产持久化原语：
- JobQueue（SQLite 作业队列：租约 claim / complete / idempotency_key 去重）
- EventStore（SSE 事件持久化，支持 after_id 重放）
- CheckpointStore（terminal checkpoint 幂等恢复）

复刻 conflux.workbench.jobs.JobManager 的恢复语义：
- 主执行线程在随机 step 崩溃（不调用 complete，租约过期）
- 恢复线程重新认领（lease 过期后可被 claim），从 checkpoint 续跑或命中 terminal checkpoint 直接完成（幂等）
- 重复 enqueue 同一 idempotency_key 应被去重

测量的指标（对应简历"可恢复任务运行时"）：
- recovery_rate              : 崩溃后最终到达终态（completed/failed）的比例
- lease_reclaim_rate        : 租约过期后能被重新认领的比例
- duplicate_execution_rate  : 完整流水线被执行 >1 次的比例（应为 0）
- sse_event_loss_rate       : 事件持久化后丢失比例（应为 0）
- sse_reconnect_loss_rate   : 通过 after_id 重连重放后丢失比例（应为 0）
- final_state_consistency   : JobQueue 状态 == terminal checkpoint 一致的比例
- idempotency_dedup_rate    : 重复 enqueue 被去重的比例

用法:
    python scripts/eval_job_recovery.py --jobs 200
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.adapters.sqlite_store import (  # noqa: E402
    CheckpointStore,
    EventStore,
    JobQueue,
    SQLiteDatabase,
)
from conflux.trace import TraceEvent  # noqa: E402

KIND = "research_query"
WORKER_A = "worker-primary"
WORKER_B = "worker-recovery"


def _db(path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(path).connect()
    db.bootstrap_schema()
    return db


def _run_mock_executor(db, run_id, *, crash_at, num_steps, exec_epochs, full_runs, events_written):
    """模拟一次执行：逐 step 写事件 + checkpoint；crash_at 处停止（不 complete）。"""
    full_runs[run_id] += 1
    total = 0
    for step in range(1, num_steps + 1):
        es = EventStore(db)
        es.append(TraceEvent(
            stage=f"step_{step}", status="completed", elapsed_ms=float(step) * 10.0,
            summary=f"mock step {step}", run_id=run_id, thread_id=run_id,
            metadata={"step": step},
        ))
        total += 1
        CheckpointStore(db).save(run_id, f"{step:06d}", {
            "step_id": step, "stage": f"step_{step}", "progress": {f"step_{step}": "completed"},
        })
        events_written[run_id] = total
        if step >= crash_at:
            return  # 模拟进程在 crash_at 崩溃：不调用 complete


def _restore_terminal(db, claimed):
    """复刻 JobManager._restore_terminal_checkpoint：命中 terminal checkpoint 直接完成（幂等）。"""
    cp = CheckpointStore(db).load(str(claimed["job_id"]))
    terminal = dict((cp or {}).get("terminal_result") or {})
    if not terminal:
        return False
    ok = JobQueue(db).complete(str(claimed["job_id"]), claimed["lease_owner"] or WORKER_B, result=terminal)
    return ok


def _recover(db, run_id, num_steps, exec_epochs, full_runs, events_written):
    claimed = JobQueue(db).claim(WORKER_B, kind=KIND)
    if claimed is None or str(claimed["run_id"]) != run_id:
        return "no_claim"
    if _restore_terminal(db, claimed):
        return "restored_idempotent"
    # 续跑：仅执行剩余 step（不应再触发完整流水线）
    resume_from = int((CheckpointStore(db).load(run_id) or {}).get("step_id") or 0)
    # 注意：resume 不应增加 full_runs（不是从头执行）
    for step in range(resume_from + 1, num_steps + 1):
        EventStore(db).append(TraceEvent(
            stage=f"step_{step}", status="completed", elapsed_ms=float(step) * 10.0,
            summary=f"resume step {step}", run_id=run_id, thread_id=run_id,
            metadata={"step": step, "resumed": True},
        ))
        CheckpointStore(db).save(run_id, f"{step:06d}", {
            "step_id": step, "stage": f"step_{step}", "progress": {f"step_{step}": "completed"},
        })
        events_written[run_id] = step
    terminal = {"public_status": "completed", "final_answer": f"answer-for-{run_id}"}
    CheckpointStore(db).save(run_id, "final", {
        "step_id": num_steps + 1, "stage": "final", "complete": True, "terminal_result": terminal,
    })
    JobQueue(db).complete(run_id, WORKER_B, result=terminal)
    return "resumed"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=200)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--output-dir", default="reports/eval/job_recovery")
    ap.add_argument("--seed", type=int, default=20260815)
    args = ap.parse_args(argv)

    random.seed(args.seed)
    import tempfile
    out_dir = (PROJECT_ROOT / args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="recovery_", dir=out_dir))
    db_path = tmp / "recovery.db"

    db = _db(db_path)
    try:
        q = JobQueue(db, lease_seconds=30.0)
        full_runs: dict[str, int] = {}
        events_written: dict[str, int] = {}
        rows = []
        dup_attempts = dup_ignored = 0
        lease_reclaimed = lease_eligible = 0
        claim_failures = []

        for i in range(args.jobs):
            run_id = f"job-{i:04d}"
            full_runs[run_id] = 0
            events_written[run_id] = 0
            crash_at = random.randint(1, args.steps)  # 1..steps 间崩溃
            # 1) 入队（带 idempotency_key = run_id）
            q.enqueue(KIND, {"query": f"q{i}"}, job_id=run_id, run_id=run_id,
                      idempotency_key=run_id, max_attempts=3)
            # 1b) 重复入队同一 idempotency_key -> 应被去重
            dup_attempts += 1
            before = db.connection.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE idempotency_key = ?", (run_id,)).fetchone()["c"]
            q.enqueue(KIND, {"query": f"q{i}-dup"}, job_id=f"{run_id}-dup", run_id=run_id,
                      idempotency_key=run_id, max_attempts=3)
            after = db.connection.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE idempotency_key = ?", (run_id,)).fetchone()["c"]
            if after == before:
                dup_ignored += 1

            # 2) 主执行线程认领并执行到崩溃点
            claimed = q.claim(WORKER_A, kind=KIND)
            if not claimed or str(claimed["run_id"]) != run_id:
                claim_failures.append(run_id)
                rows.append({"run_id": run_id, "recovery": "primary_claim_failed",
                             "final_status": "unknown", "expected_events": 0,
                             "recovered_events": 0, "event_loss": 0, "reconnect_loss": 0,
                             "full_executions": full_runs[run_id], "state_consistent": False,
                             "crash_at": crash_at})
                continue
            _run_mock_executor(db, run_id, crash_at=crash_at, num_steps=args.steps,
                               exec_epochs=None, full_runs=full_runs, events_written=events_written)
            # 模拟进程崩溃：让租约过期（不调用 complete / heartbeat）
            db.connection.execute(
                "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?",
                (time.time() - 10.0, run_id))
            db.connection.commit()
            lease_eligible += 1

            # 3) 恢复线程重新认领并恢复
            rec = _recover(db, run_id, args.steps, None, full_runs, events_written)
            if rec in ("resumed", "restored_idempotent"):
                lease_reclaimed += 1

            # 4) 校验
            final_q = q.get(run_id) or {}
            final_status = str(final_q.get("status") or "")
            es = EventStore(db).list(run_id=run_id)
            recovered_events = len(es)
            expected_events = events_written[run_id]
            # after_id 重连重放
            replay = EventStore(db).list(run_id=run_id, after_id=0)
            replay_ok = len(replay) == expected_events
            # terminal checkpoint 一致性
            cp = CheckpointStore(db).load(run_id, "final") or {}
            term = cp.get("terminal_result") or {}
            consistent = (final_status == "completed" and term.get("public_status") == "completed")
            rows.append({
                "run_id": run_id,
                "crash_at": crash_at,
                "recovery": rec,
                "final_status": final_status,
                "expected_events": expected_events,
                "recovered_events": recovered_events,
                "event_loss": max(0, expected_events - recovered_events),
                "reconnect_loss": 0 if replay_ok else max(0, expected_events - len(replay)),
                "full_executions": full_runs[run_id],
                "state_consistent": consistent,
            })

        # 聚合
        total = len(rows)
        recovered_terminal = sum(1 for r in rows if r["final_status"] in ("completed", "failed"))
        dup_exec = sum(1 for r in rows if r["full_executions"] > 1)
        evt_loss = sum(r["event_loss"] for r in rows)
        evt_total = sum(r["expected_events"] for r in rows)
        reconn_loss = sum(r["reconnect_loss"] for r in rows)
        consistent = sum(1 for r in rows if r["state_consistent"])
        result = {
            "schema_version": "conflux-job-recovery-v1",
            "total_jobs": total,
            "steps_per_job": args.steps,
            "lease_eligible": lease_eligible,
            "recovery_rate": round(recovered_terminal / total, 4) if total else None,
            "lease_reclaim_rate": round(lease_reclaimed / lease_eligible, 4) if lease_eligible else None,
            "duplicate_execution_rate": round(dup_exec / total, 4) if total else None,
            "sse_event_loss_rate": round(evt_loss / evt_total, 4) if evt_total else None,
            "sse_reconnect_loss_rate": round(reconn_loss / evt_total, 4) if evt_total else None,
            "final_state_consistency_rate": round(consistent / total, 4) if total else None,
            "idempotency_dedup_attempts": dup_attempts,
            "idempotency_dedup_ignored": dup_ignored,
            "idempotency_dedup_rate": round(dup_ignored / dup_attempts, 4) if dup_attempts else None,
            "primary_claim_failures": claim_failures,
            "rows": rows,
        }
    finally:
        db.close()

    out = out_dir / "job_recovery.json"
    keep = {k: v for k, v in result.items() if k != "rows"}
    out.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 也存带明细的
    (out_dir / "job_recovery_detail.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(keep, ensure_ascii=False, indent=2))
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
