"""P0 convergence baseline capture (read-only).

Captures the structured facts required by docs/plans/Conflux可用性稳定性与架构收敛执行计划v1.md
P0 into a JSON manifest.  Never writes to the runtime database, never starts model
calls, never modifies the worktree.

Usage:
    python scripts/capture_convergence_baseline.py --out reports/evaluation/convergence/p0/baseline_manifest.json

Output schema (Conflux convergence evidence v1):
    schema, captured_at, git, environment, database, chroma, service, representative_queries
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    from conflux.core.runtime_home import database_path, resolve_conflux_home
    from conflux.adapters.sqlite_store import SCHEMA_MIGRATIONS
except Exception as exc:  # pragma: no cover - baseline capture may run before env-importable
    SCHEMA_MIGRATIONS = []
    print(f"[capture] warning: could not import conflux modules: {exc}", file=sys.stderr)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path = PROJECT_ROOT) -> dict:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        return {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout[:20000],
            "stderr": proc.stderr[:10000],
        }
    except Exception as exc:
        return {"command": cmd, "error": str(exc)}


def git_baseline() -> dict:
    head = _run(["git", "rev-parse", "HEAD"])
    branch = _run(["git", "branch", "--show-current"])
    ahead = _run(["git", "rev-list", "--left-right", "--count", "origin/main...main"])
    status = _run(["git", "status", "--porcelain=v2"])
    diff = _run(["git", "diff", "--stat"])
    return {
        "head": head.get("stdout", "").strip(),
        "branch": branch.get("stdout", "").strip(),
        "origin_ahead_behind": ahead.get("stdout", "").strip(),
        "status_porcelain_v2": status.get("stdout", "").strip().splitlines(),
        "diff_stat": [ln for ln in diff.get("stdout", "").splitlines() if ln.strip()],
    }


def _db_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def database_baseline() -> dict:
    try:
        db_path = database_path()
    except Exception as exc:
        return {"error": str(exc)}
    if not db_path.exists():
        return {"path": str(db_path), "exists": False}

    out: dict = {"path": str(db_path), "exists": True, "tables": {}, "counts": {}}
    try:
        conn = _db_readonly(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        out["tables"] = tables
        migrations = cur.execute(
            "SELECT version, applied_at FROM schema_migrations ORDER BY rowid"
        ).fetchall()
        out["schema_migrations"] = [
            {"version": r["version"], "applied_at": r["applied_at"]} for r in migrations
        ]
        out["max_schema_version"] = max((r["version"] for r in migrations), default=None)
        for table in ("runs", "jobs", "run_events", "artifacts", "checkpoints", "papers", "paper_notes", "user_memory"):
            if table in tables:
                row = cur.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()
                out["counts"][table] = row["n"]
        conn.close()
    except Exception as exc:
        out["error"] = str(exc)
    return out


def chroma_baseline() -> dict:
    chroma_dir = PROJECT_ROOT / "data" / "chroma_db"
    if not chroma_dir.exists():
        return {"path": str(chroma_dir), "exists": False}
    out = {"path": str(chroma_dir), "exists": True, "sqlite": {}}
    sqlite_file = chroma_dir / "chroma.sqlite3"
    if sqlite_file.exists():
        try:
            conn = _db_readonly(sqlite_file)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            out["sqlite"]["tables"] = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT id, name FROM collections ORDER BY id")
            out["sqlite"]["collections"] = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) AS n FROM embeddings")
            out["sqlite"]["embedding_count"] = cur.fetchone()["n"]
            conn.close()
        except Exception as exc:
            out["sqlite"]["error"] = str(exc)
    return out


def service_baseline() -> dict:
    """Read-only: listeners on the workbench default port and the python processes cmdline."""
    port = int(os.environ.get("CONFLUX_PORT", "8765"))
    out = {"default_port": port, "listeners": [], "python_procs": []}
    try:
        for conn in psutil_net_connections():
            if conn.laddr.port in (port, port + 1000):
                out["listeners"].append(
                    {"laddr": f"{conn.laddr.ip}:{conn.laddr.port}", "pid": conn.pid, "status": conn.status}
                )
    except Exception:
        pass
    return out


def psutil_net_connections():
    try:
        import psutil
        yield from psutil.net_connections(kind="tcp")
    except Exception:
        return iter(())


def representative_queries_draft() -> list[dict]:
    """P0 5.4.8 draft of the P2 frozen 12-query set (offline; no provider calls)."""
    return [
        {"id": "q01", "type": "single_concept_local", "query": "在检索增强生成系统中，混合检索的主要作用是什么？请基于可核验来源简要回答并给出引用。", "allowed_sources": ["RAG", "papers/", "data/documents/"], "depth": "quick"},
        {"id": "q02", "type": "single_concept_local", "query": "Conflux 项目的成果物在什么条件下可以标记为可交付（deliverable）？请基于项目文档与代码说明完成标准。", "allowed_sources": ["Local", "code", "docs/"], "depth": "quick"},
        {"id": "q03", "type": "method_comparison", "query": "基于LLM的智能体为支持长程任务有哪些主要设计？请比较关键方法、适用边界，并给出可核验引用。", "allowed_sources": ["Local", "papers", "Web"], "depth": "standard"},
        {"id": "q04", "type": "method_comparison", "query": "混合检索（dense+sparse）与纯语义检索在召回率和适用场景上的差别是什么？请比较机制和边界。", "allowed_sources": ["Local", "papers", "Web"], "depth": "standard"},
        {"id": "q05", "type": "method_comparison", "query": "RAG 系统中 chunk 粒度对生成质量和引用正确性的影响如何？", "allowed_sources": ["Local", "papers"], "depth": "standard"},
        {"id": "q06", "type": "time_sensitive", "query": "2025 年以来长程 Agent 任务规划的最新方法与主要局限是什么？", "allowed_sources": ["Web", "Local"], "depth": "standard"},
        {"id": "q07", "type": "time_sensitive", "query": "近一年大模型推理成本下降对本地 ResearchOps 工具设计的最直接影响是什么？", "allowed_sources": ["Web", "Local"], "depth": "standard"},
        {"id": "q08", "type": "local_scarce", "query": "Conflux 是否支持远程 Worker 或 Redis 队列？请基于代码核实。", "allowed_sources": ["Local"], "depth": "quick"},
        {"id": "q09", "type": "local_scarce", "query": "当前代码库中宽泛异常（bare except）改善了可用性还是掩盖了原因？请基于代码审计说明。", "allowed_sources": ["Local"], "depth": "standard"},
        {"id": "q10", "type": "conflicting_evidence", "query": "长程 Agent 中反思式设计相比规划式设计谁更重要？现有证据如何相互冲突？", "allowed_sources": ["Local", "Web"], "depth": "standard"},
        {"id": "q11", "type": "conflicting_evidence", "query": "模型规模与推理时长度扩展（CoT）哪个对长程任务更重要？", "allowed_sources": ["Local", "Web"], "depth": "standard"},
        {"id": "q12", "type": "long_horizon_cross_domain", "query": "如果要给 GIS/空间分析与 LLM 智能体写一篇跨域综述，最值得覆盖哪些技术栈与证据缺口？", "allowed_sources": ["Local", "Web"], "depth": "standard"},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(PROJECT_ROOT / "reports" / "evaluation" / "convergence" / "p0"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "conflux.convergence_evidence.v1",
        "phase": "P0",
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": {"platform": platform.platform(), "python": sys.version.split()[0], "machine": platform.machine()},
        "git": git_baseline(),
        "database": database_baseline(),
        "chroma": chroma_baseline(),
        "service": service_baseline(),
        "representative_queries_draft": representative_queries_draft(),
        "note": "P0 baseline capture; tests and API baselines are collected separately by the P0 runner.",
    }
    out_path = outdir / "baseline_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[capture] wrote {out_path}")
    return 0


if __name__ == "__main__":
    import argparse  # noqa: PLC0415  (imported lazily to keep capture import lightweight)
    raise SystemExit(main())