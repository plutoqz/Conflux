"""P4.3 D 实验追踪 — migration 0010 + repository + 注册应用服务（D1）。

设计对照 docs/plans/p4/D_实验追踪与导师周报.md：
- 存储：SQLite migration 0010_experiments（最小字段 + JSON 列扩展）；
- 采集三路统一走 ``experiment_register`` 应用服务（CLI 登记 / 产物扫描约定 /
  对话登记经 ApprovalRequest），全部带 ``source_ref`` 回源，同键幂等；
- 状态机 draft → running → done / failed；``linked_claims``
  （claim:{id}:{verdict}）引用 P3.4 链接层证据 ref 风格，进入周期审计
  ``cycle_audit._diff_experiments`` 与周期摘要导出。

通用性：schema 与命令均为通用形状，不硬编码 Conflux/FusionAgent 专有字段。
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

EXPERIMENT_STATUSES = ("draft", "running", "done", "failed")

EXPERIMENT_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS experiments (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        hypothesis TEXT NOT NULL DEFAULT '',
        params_json TEXT NOT NULL DEFAULT '{}',
        metrics_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'draft',
        commit_hash TEXT NOT NULL DEFAULT '',
        artifacts_json TEXT NOT NULL DEFAULT '[]',
        linked_claims_json TEXT NOT NULL DEFAULT '[]',
        source_ref TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        UNIQUE(project_id, source_ref)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_experiments_project ON experiments(project_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_experiments_project_created ON experiments(project_id, created_at)",
]


def register_experiments_migration() -> None:
    """把 0010 追加进全局 SCHEMA_MIGRATIONS（幂等，import 时调用）。"""

    from conflux.adapters import sqlite_store as store

    versions = {item[0] for item in store.SCHEMA_MIGRATIONS}
    if "0010_experiments" not in versions:
        store.SCHEMA_MIGRATIONS.append(("0010_experiments", list(EXPERIMENT_STATEMENTS)))


register_experiments_migration()


def _json_dumps(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return payload.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def _json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class ExperimentRepository:
    """experiments 表 CRUD；source_ref 同键幂等；数字/哈希字段直接落库。"""

    def __init__(self, db: Any) -> None:
        self.db = db

    def register(
        self,
        *,
        project_id: str,
        name: str,
        hypothesis: str = "",
        params: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        status: str = "draft",
        commit_hash: str = "",
        artifacts: list[str] | None = None,
        linked_claims: list[str] | None = None,
        source_ref: str = "",
    ) -> dict[str, Any]:
        """登记一个实验（三路采集统一入口）；同 (project_id, name, source_ref) 幂等。"""
        name = str(name or "").strip()
        if not name:
            raise ValueError("实验名为必填（name）")
        status = str(status or "draft")
        if status not in EXPERIMENT_STATUSES:
            raise ValueError(f"无效实验状态：{status}（应为 draft/running/done/failed）")
        source_ref = str(source_ref or "")
        if not source_ref:
            source_ref = f"manual:{uuid.uuid4().hex[:16]}"
        now = time.time()
        # 同键幂等：同一项目同一 source_ref 已存在则直接返回既有记录。
        existing = self.by_source_ref(project_id, source_ref)
        if existing is not None:
            return existing
        import hashlib

        digest = hashlib.sha256(f"{project_id}|{name}|{source_ref}".encode("utf-8")).hexdigest()[:16]
        experiment_id = f"exp-{digest}"
        self.db.connection.execute(
            """
            INSERT INTO experiments (
                id, project_id, name, hypothesis, params_json, metrics_json,
                status, commit_hash, artifacts_json, linked_claims_json,
                source_ref, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id, str(project_id), name, str(hypothesis),
                _json_dumps(dict(params or {})), _json_dumps(dict(metrics or {})),
                status, str(commit_hash), _json_dumps(list(artifacts or [])),
                _json_dumps(list(linked_claims or [])), source_ref, now, now,
            ),
        )
        self.db.connection.commit()
        return self.get(experiment_id) or {}

    def update_status(self, experiment_id: str, status: str) -> dict[str, Any] | None:
        if status not in EXPERIMENT_STATUSES:
            raise ValueError(f"无效实验状态：{status}")
        cursor = self.db.connection.execute(
            "UPDATE experiments SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), experiment_id),
        )
        self.db.connection.commit()
        return self.get(experiment_id) if cursor.rowcount else None

    def attach_metric(self, experiment_id: str, key: str, value: Any) -> dict[str, Any] | None:
        experiment = self.get(experiment_id)
        if experiment is None:
            return None
        metrics = dict(experiment.get("metrics") or {})
        metrics[str(key)] = value
        self.db.connection.execute(
            "UPDATE experiments SET metrics_json = ?, updated_at = ? WHERE id = ?",
            (_json_dumps(metrics), time.time(), experiment_id),
        )
        self.db.connection.commit()
        return self.get(experiment_id)

    def attach_claim(self, experiment_id: str, claim_ref: str) -> dict[str, Any] | None:
        experiment = self.get(experiment_id)
        if experiment is None or not str(claim_ref).startswith("claim:"):
            return experiment
        claims = [entry for entry in (experiment.get("linked_claims") or []) if entry != claim_ref]
        claims.append(claim_ref)
        self.db.connection.execute(
            "UPDATE experiments SET linked_claims_json = ?, updated_at = ? WHERE id = ?",
            (_json_dumps(claims), time.time(), experiment_id),
        )
        self.db.connection.commit()
        return self.get(experiment_id)

    def list(
        self,
        project_id: str,
        *,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if status:
            rows = self.db.connection.execute(
                "SELECT * FROM experiments WHERE project_id = ? AND status = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, status, max(1, int(limit))),
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM experiments WHERE project_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, max(1, int(limit))),
            ).fetchall()
        return [self._row(row) for row in rows]

    def list_period(
        self,
        project_id: str,
        start: float,
        end: float,
    ) -> list[dict[str, Any]]:
        """周期内（start < created_at <= end）或周期内完成/失败的实验。"""
        rows = self.db.connection.execute(
            "SELECT * FROM experiments WHERE project_id = ? AND created_at > ? AND created_at <= ? "
            "ORDER BY created_at DESC",
            (project_id, start, end),
        ).fetchall()
        result = [self._row(row) for row in rows]
        seen = {entry["id"] for entry in result}
        if start > 0:
            rows = self.db.connection.execute(
                "SELECT * FROM experiments WHERE project_id = ? AND created_at <= ? "
                "AND updated_at > ? AND updated_at <= ? ORDER BY updated_at DESC",
                (project_id, start, start, end),
            ).fetchall()
            for row in rows:
                item = self._row(row)
                if item["id"] not in seen:
                    result.append(item)
                    seen.add(item["id"])
        return result

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        return self._row(row) if row else None

    def by_source_ref(self, project_id: str, source_ref: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM experiments WHERE project_id = ? AND source_ref = ?",
            (project_id, source_ref),
        ).fetchone()
        return self._row(row) if row else None

    def count(self, project_id: str, *, status: str | None = None) -> int:
        if status:
            row = self.db.connection.execute(
                "SELECT COUNT(*) AS n FROM experiments WHERE project_id = ? AND status = ?",
                (project_id, status),
            ).fetchone()
        else:
            row = self.db.connection.execute(
                "SELECT COUNT(*) AS n FROM experiments WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _row(row: Any) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "name": str(row["name"]),
            "hypothesis": str(row["hypothesis"]),
            "params": _json_loads(row["params_json"], {}),
            "metrics": _json_loads(row["metrics_json"], {}),
            "status": str(row["status"]),
            "commit_hash": str(row["commit_hash"]),
            "artifacts": _json_loads(row["artifacts_json"], []),
            "linked_claims": _json_loads(row["linked_claims_json"], []),
            "source_ref": str(row["source_ref"]),
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
        }


def open_experiment_repo() -> tuple[ExperimentRepository, Any]:
    """打开运行时 DB 的实验仓库（bootstrap 幂等；调用方负责 close .db）。"""
    from conflux.adapters.sqlite_store import SQLiteDatabase
    from conflux.core.runtime_home import database_path

    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    return ExperimentRepository(db), db


# ── 产物扫描（采集路 2：results*.json 键约定）──────────────────────


def auto_scan_result_files(project: Any) -> list[str]:
    """扫描 project 结果目录下的 results*.json（D §2 键约定），登记为实验批次。

    同 (project, name, source_ref) 幂等（source_ref = scan:{path}）；
    只读取结果目录内小型 JSON 结果文件，代码/文档目录不触碰。
    """
    root = Path(getattr(project, "path", "") or "").expanduser().resolve()
    if not root.exists():
        return []
    dirs: list[Path] = [root]
    for name in (getattr(project, "result_dirs", None) or []):
        candidate = root / str(name)
        if candidate.is_dir():
            dirs.append(candidate)
    registered: list[str] = []
    for directory in dirs:
        try:
            files = sorted(directory.glob("results*.json"))
        except OSError:
            continue
        for path in files:
            try:
                if path.stat().st_size > 200_000:
                    continue
                payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if not isinstance(payload, dict) or not payload.get("name") or "metrics" not in payload:
                continue
            entry = experiment_register(
                project_id=project.id,
                name=str(payload["name"]),
                hypothesis=str(payload.get("hypothesis") or ""),
                params=dict(payload.get("params") or {}),
                metrics=dict(payload.get("metrics") or {}),
                commit_hash=str(payload.get("commit") or ""),
                status=str(payload.get("status") or "done"),
                source_ref=f"scan:{path.name}",
            )
            if entry.get("id"):
                registered.append(str(entry["id"]))
    return registered


def experiment_register(
    *,
    project_id: str,
    name: str,
    hypothesis: str = "",
    params: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    status: str = "draft",
    commit_hash: str = "",
    artifacts: list[str] | None = None,
    linked_claims: list[str] | None = None,
    source_ref: str = "",
) -> dict[str, Any]:
    """应用层登记入口（CLI / 扫描 / 对话三路共用）；打开独立连接并关闭。"""
    repo, db = open_experiment_repo()
    try:
        return repo.register(
            project_id=project_id,
            name=name,
            hypothesis=hypothesis,
            params=params,
            metrics=metrics,
            status=status,
            commit_hash=commit_hash,
            artifacts=artifacts,
            linked_claims=linked_claims,
            source_ref=source_ref,
        )
    finally:
        db.close()