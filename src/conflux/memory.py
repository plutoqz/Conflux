"""P4.0 A 用户记忆与技能库：0009_user_memory + repository + 采集器 + 召回/注入。

设计对照 docs/plans/p4/A_用户记忆与技能库.md：
- 存储：SQLite migration 0009（fact/preference/feedback/reference/skill_ref），
  supersedes 链 + pending 队列 + 容量上限 500；
- 采集：确定性触发（报告反馈/雷达覆写/周期 confirm 直接 active；对话纠正/
  高频术语入 pending），全部带 source_event_id 回源，同源幂等；
- 注入：≤5 条、≤300 token、kind 白名单（preference/feedback/reference，
  fact 禁入）、sanitize 清洗、明示"证据结论优先"。

通用性：schema 与触发事件均为通用形状，不硬编码 Conflux/FusionAgent 专有字段。
"""

from __future__ import annotations

import json
import re
import time
import uuid
from math import ceil
from typing import Any, Iterable

from .sanitize import sanitize_untrusted_content

CAPACITY_LIMIT = 500
INJECTABLE_KINDS = ("preference", "feedback", "reference")
MAX_INJECT_ENTRIES = 5
MAX_INJECT_TOKENS = 300
DEDUP_THRESHOLD = 0.72
MEMORY_KINDS = ("fact", "preference", "feedback", "reference", "skill_ref")
_DESCRIPTION_MAX_CHARS = 120

_MEMORY_BANNER_PREFIX = "用户偏好参考（证据结论优先，记忆不得覆盖证据裁决）："

USER_MEMORY_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS user_memory (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        content_json TEXT NOT NULL,
        description TEXT NOT NULL,
        source_event_id TEXT NOT NULL DEFAULT '',
        source_run_id TEXT NOT NULL DEFAULT '',
        project_id TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        supersedes_id TEXT NOT NULL DEFAULT '',
        confidence REAL NOT NULL DEFAULT 0.5,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_user_memory_status ON user_memory(status)",
    "CREATE INDEX IF NOT EXISTS idx_user_memory_kind ON user_memory(kind, status)",
    "CREATE INDEX IF NOT EXISTS idx_user_memory_project ON user_memory(project_id, status)",
]


def register_user_memory_migration() -> None:
    """把 0009 追加进全局 SCHEMA_MIGRATIONS（幂等，import 时调用）。"""

    from conflux.adapters import sqlite_store as store

    versions = {item[0] for item in store.SCHEMA_MIGRATIONS}
    if "0009_user_memory" not in versions:
        store.SCHEMA_MIGRATIONS.append(("0009_user_memory", list(USER_MEMORY_STATEMENTS)))


register_user_memory_migration()


class MemoryCapacityError(RuntimeError):
    """active 条目达到容量上限且无法 supersede 时抛出。"""


def _description_tokens(description: str) -> set[str]:
    """描述分词：ASCII 小写词 + CJK 双字组，用于相似度与召回排序。"""

    text = str(description or "").casefold()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    tokens.update("".join(pair) for pair in zip(cjk, cjk[1:]))
    return tokens


def description_similarity(a: str, b: str) -> float:
    """Jaccard 相似度（token 集合）。"""

    left, right = _description_tokens(a), _description_tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _estimate_tokens(text: str) -> int:
    """沿用 model_factory 的保守估算（≈字符数/1.5）。"""

    return max(1, ceil(len(str(text)) / 1.5))


class UserMemoryRepository:
    """user_memory 表 CRUD + supersedes 链 + pending 确认门 + 容量上限。"""

    def __init__(self, db: Any) -> None:
        self.db = db

    def add(
        self,
        *,
        kind: str,
        content: dict[str, Any],
        description: str,
        source_event_id: str = "",
        source_run_id: str = "",
        project_id: str = "",
        confidence: float = 1.0,
        status: str = "active",
    ) -> str:
        kind = str(kind or "")
        if kind not in MEMORY_KINDS:
            raise ValueError(f"unsupported memory kind: {kind}")
        description = str(description or "").strip()[: _DESCRIPTION_MAX_CHARS]
        if not description:
            raise ValueError("description required (召回用一句话描述)")
        # 同源幂等：同一 source_event_id 已存在则直接返回既有条目。
        if source_event_id:
            existing = self.by_source_event(source_event_id, kind=kind)
            if existing:
                return str(existing["id"])
        now = time.time()
        memory_id = f"memory-{uuid.uuid4().hex[:16]}"
        # 去重链：同 kind + description 相似度 ≥ 阈值 → 新条目 supersedes 旧条目。
        supersedes: str | None = None
        for entry in self.list(kind=kind, status="active", limit=CAPACITY_LIMIT):
            if description_similarity(description, str(entry.get("description") or "")) >= DEDUP_THRESHOLD:
                supersedes = str(entry["id"])
                break
        if supersedes is None:
            active_count = self.count(status="active")
            if active_count >= CAPACITY_LIMIT:
                raise MemoryCapacityError(
                    f"user_memory 容量上限 {CAPACITY_LIMIT} 已满；请清理或 supersede 既有条目"
                )
        row = {
            "id": memory_id,
            "kind": kind,
            "content_json": json.dumps(content or {}, ensure_ascii=False, sort_keys=True),
            "description": description,
            "source_event_id": str(source_event_id or ""),
            "source_run_id": str(source_run_id or ""),
            "project_id": str(project_id or ""),
            "status": "pending" if status == "pending" else "active",
            "supersedes_id": supersedes or "",
            "confidence": max(0.0, min(1.0, float(confidence))),
            "created_at": now,
            "updated_at": now,
        }
        self.db.connection.execute(
            """
            INSERT INTO user_memory
                (id, kind, content_json, description, source_event_id, source_run_id,
                 project_id, status, supersedes_id, confidence, created_at, updated_at)
            VALUES
                (:id, :kind, :content_json, :description, :source_event_id, :source_run_id,
                 :project_id, :status, :supersedes_id, :confidence, :created_at, :updated_at)
            """,
            row,
        )
        if supersedes:
            self.db.connection.execute(
                "UPDATE user_memory SET status='superseded', supersedes_id=:new_id, updated_at=:now "
                "WHERE id=:old_id",
                {"new_id": memory_id, "now": now, "old_id": supersedes},
            )
        self.db.connection.commit()
        return memory_id

    def list(
        self,
        *,
        kind: str | None = None,
        status: str | None = None,
        project_id: str | None = None,
        limit: int = CAPACITY_LIMIT,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if kind:
            clauses.append("kind = :kind")
            params["kind"] = kind
        if status:
            clauses.append("status = :status")
            params["status"] = status
        if project_id:
            clauses.append("project_id = :project_id")
            params["project_id"] = project_id
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.connection.execute(
            f"SELECT * FROM user_memory {where} ORDER BY created_at DESC LIMIT :limit",
            {**params, "limit": max(1, int(limit))},
        ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        rows = self.db.connection.execute(
            "SELECT * FROM user_memory WHERE id = :id", {"id": memory_id}
        ).fetchall()
        return _row_to_entry(rows[0]) if rows else None

    def by_source_event(self, source_event_id: str, *, kind: str | None = None) -> dict[str, Any] | None:
        if not source_event_id:
            return None
        if kind:
            rows = self.db.connection.execute(
                "SELECT * FROM user_memory WHERE source_event_id = :eid AND kind = :kind ORDER BY created_at DESC LIMIT 1",
                {"eid": source_event_id, "kind": kind},
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM user_memory WHERE source_event_id = :eid ORDER BY created_at DESC LIMIT 1",
                {"eid": source_event_id},
            ).fetchall()
        return _row_to_entry(rows[0]) if rows else None

    def count(self, *, status: str | None = None) -> int:
        if status:
            rows = self.db.connection.execute(
                "SELECT COUNT(*) AS n FROM user_memory WHERE status = :status", {"status": status}
            ).fetchall()
        else:
            rows = self.db.connection.execute("SELECT COUNT(*) AS n FROM user_memory").fetchall()
        return int(rows[0]["n"]) if rows else 0

    def confirm(self, memory_id: str) -> dict[str, Any] | None:
        """pending → active（确认门）。"""

        entry = self.get(memory_id)
        if entry is None or entry["status"] != "pending":
            return None
        self.db.connection.execute(
            "UPDATE user_memory SET status='active', updated_at=:now WHERE id=:id",
            {"id": memory_id, "now": time.time()},
        )
        self.db.connection.commit()
        return self.get(memory_id)

    def reject(self, memory_id: str) -> dict[str, Any] | None:
        """pending → rejected（确认门）。"""

        entry = self.get(memory_id)
        if entry is None or entry["status"] != "pending":
            return None
        self.db.connection.execute(
            "UPDATE user_memory SET status='rejected', updated_at=:now WHERE id=:id",
            {"id": memory_id, "now": time.time()},
        )
        self.db.connection.commit()
        return self.get(memory_id)

    def recall(
        self,
        query: str,
        *,
        kinds: Iterable[str] = INJECTABLE_KINDS,
        limit: int = MAX_INJECT_ENTRIES,
    ) -> list[dict[str, Any]]:
        """按 description 与查询的相关度排序召回 active 条目（fact 默认禁入）。"""

        allowed = tuple(kinds)
        candidates = [
            entry for entry in self.list(status="active", limit=CAPACITY_LIMIT)
            if entry["kind"] in allowed
        ]
        scored = sorted(
            candidates,
            key=lambda entry: description_similarity(str(query or ""), str(entry.get("description") or "")),
            reverse=True,
        )
        return scored[: max(1, int(limit))]


def _row_to_entry(row: Any) -> dict[str, Any]:
    payload = dict(row) if isinstance(row, dict) else {key: row[key] for key in row.keys()}
    payload["content"] = _safe_json(payload.pop("content_json", "{}"))
    return payload


def _safe_json(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    try:
        return json.loads(str(value or "{}"))
    except (TypeError, ValueError):
        return {}


def build_memory_banner(
    entries: Iterable[dict[str, Any]],
    *,
    max_entries: int = MAX_INJECT_ENTRIES,
    max_tokens: int = MAX_INJECT_TOKENS,
) -> str:
    """注入前缀：白名单过滤 → sanitize 清洗 → 条数/总量双上限 → 免责声明。"""

    lines: list[str] = []
    for entry in entries:
        if len(lines) >= max_entries:
            break
        kind = str(entry.get("kind") or "")
        if kind not in INJECTABLE_KINDS or str(entry.get("status") or "") != "active":
            continue
        description = str(entry.get("description") or "").strip()
        content = entry.get("content") or {}
        text = description
        if isinstance(content, dict) and content.get("text"):
            text = f"{description}：{str(content['text'])}"
        cleaned, _ = sanitize_untrusted_content(text)
        lines.append(f"- {kind}：{cleaned}")
    if not lines:
        return ""
    banner = _MEMORY_BANNER_PREFIX + "\n" + "\n".join(lines)
    while lines and _estimate_tokens(banner) > max_tokens:
        lines.pop()
        banner = _MEMORY_BANNER_PREFIX + "\n" + "\n".join(lines)
    return banner


def recall_for_query(query: str, *, max_entries: int = MAX_INJECT_ENTRIES) -> str:
    """运行入口钩子：召回 + 注入一次成型；任何失败都返回空串（记忆不得拖垮运行）。"""

    try:
        from conflux.adapters.sqlite_store import SQLiteDatabase
        from conflux.core.runtime_home import database_path

        db = SQLiteDatabase(database_path()).connect()
        db.bootstrap_schema()
        try:
            entries = UserMemoryRepository(db).recall(query)
            return build_memory_banner(entries, max_entries=max_entries)
        finally:
            db.close()
    except Exception:
        return ""


class MemoryCollector:
    """确定性触发采集器（对照 A 设计 §3）。

    - 直接入 active：报告反馈/结论纠正（feedback）、雷达决策覆写（preference）、
      周期审计 confirm（fact，项目级）；
    - 入 pending：对话纠正（preference）、高频术语（preference）；
    - 全部携带 source_event_id 回源；同 source_event_id + kind 幂等（repo 层去重）。
    """

    def __init__(self, repo: UserMemoryRepository) -> None:
        self.repo = repo

    def collect(self, event: dict[str, Any]) -> str | None:
        """event: {type, source_event_id, source_run_id?, project_id?, payload}。"""

        event_type = str(event.get("type") or "")
        payload = event.get("payload") or {}
        if not isinstance(payload, dict) or not str(event.get("source_event_id") or ""):
            return None
        common = {
            "source_event_id": str(event["source_event_id"]),
            "source_run_id": str(event.get("source_run_id") or ""),
            "project_id": str(event.get("project_id") or ""),
            "confidence": max(0.0, min(1.0, float(payload.get("confidence") or 1.0))),
        }
        if event_type == "report_feedback":
            return self.repo.add(
                kind="feedback",
                content={"text": str(payload.get("text") or ""), "corrected": bool(payload.get("corrected") or False)},
                description=_clip(str(payload.get("summary") or payload.get("text") or ""), "结论纠正反馈"),
                status="active",
                **common,
            )
        if event_type == "radar_override":
            return self.repo.add(
                kind="preference",
                content={"paper": str(payload.get("paper") or ""), "decision": str(payload.get("decision") or "")},
                description=_clip(
                    str(payload.get("summary") or ""),
                    f"雷达决策覆写：{str(payload.get('decision') or '')}",
                ),
                status="active",
                **common,
            )
        if event_type == "cycle_confirmed":
            return self.repo.add(
                kind="fact",
                content={"accepted": bool(payload.get("accepted") or True)},
                description=_clip(
                    str(payload.get("summary") or ""),
                    "周期审计确认：本周期验收标准达成",
                ),
                status="active",
                **common,
            )
        if event_type == "chat_correction":
            return self.repo.add(
                kind="preference",
                content={"text": str(payload.get("text") or "")},
                description=_clip(str(payload.get("text") or ""), "对话纠正偏好"),
                status="pending",
                **common,
            )
        if event_type == "term_suggestion":
            return self.repo.add(
                kind="preference",
                content={"term": str(payload.get("term") or ""), "count": int(payload.get("count") or 0)},
                description=_clip(
                    str(payload.get("summary") or ""),
                    f"高频术语偏好：{str(payload.get('term') or '')}",
                ),
                status="pending",
                **common,
            )
        return None


def _clip(text: str, fallback: str) -> str:
    value = str(text or "").strip()
    return (value or fallback)[: _DESCRIPTION_MAX_CHARS]
