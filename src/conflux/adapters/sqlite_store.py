"""SQLite-backed persistence for M3 runtime state.

This module implements the first M3 slice: runs, run steps, trace events,
approvals, and immutable artifact references.  Each store is intentionally
small and reads/writes JSON columns so contracts can evolve without schema
churn.
"""

from __future__ import annotations

import json
import hashlib
import sqlite3
import time
import uuid
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from conflux.core.contracts import ApprovalRequest, ArtifactRef, StepResult


SCHEMA_MIGRATIONS = [
    (
        "0001_runtime_state",
        [
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                workspace TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                thread_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS run_steps (
                step_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                plugin_id TEXT NOT NULL DEFAULT '',
                capability_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                output_json TEXT NOT NULL DEFAULT '{}',
                evidence_json TEXT NOT NULL DEFAULT '[]',
                artifact_refs_json TEXT NOT NULL DEFAULT '[]',
                metrics_json TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps(run_id, seq)",
            """
            CREATE TABLE IF NOT EXISTS run_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL DEFAULT '',
                thread_id TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT,
                summary TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                elapsed_ms REAL NOT NULL DEFAULT 0,
                timestamp REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_run_events_run ON run_events(run_id, event_id)",
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL DEFAULT '',
                operation TEXT NOT NULL,
                diff_json TEXT NOT NULL DEFAULT '{}',
                risk TEXT NOT NULL DEFAULT 'low',
                input_hash TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_approvals_result ON approvals(result)",
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                location TEXT NOT NULL,
                source_run_id TEXT NOT NULL DEFAULT '',
                source_step_id TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(source_run_id)",
        ],
    ),
    (
        "0002_jobs_checkpoints",
        [
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                idempotency_key TEXT UNIQUE,
                run_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 0,
                scheduled_at REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                lease_owner TEXT,
                lease_expires_at REAL,
                last_heartbeat_at REAL,
                error TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_jobs_status_scheduled ON jobs(status, scheduled_at, priority DESC)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_kind_status ON jobs(kind, status)",
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (thread_id, step_id)
            )
            """,
        ],
    ),
    (
        "0003_p2_research_state",
        [
            "ALTER TABLE jobs ADD COLUMN result_json TEXT NOT NULL DEFAULT '{}'",
            """
            CREATE TABLE IF NOT EXISTS papers (
                paper_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                canonical_id TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT '',
                doi TEXT NOT NULL DEFAULT '',
                title_hash TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(source, canonical_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS project_papers (
                project_id TEXT NOT NULL,
                paper_key TEXT NOT NULL REFERENCES papers(paper_key) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'discovered',
                matched_intent_ids_json TEXT NOT NULL DEFAULT '[]',
                matched_track_ids_json TEXT NOT NULL DEFAULT '[]',
                matched_rq_ids_json TEXT NOT NULL DEFAULT '[]',
                matched_milestone_ids_json TEXT NOT NULL DEFAULT '[]',
                evidence_utility TEXT NOT NULL DEFAULT 'none',
                relevance REAL NOT NULL DEFAULT 0,
                urgency REAL NOT NULL DEFAULT 0,
                novelty REAL NOT NULL DEFAULT 0,
                review_confidence REAL NOT NULL DEFAULT 0,
                profile_version TEXT NOT NULL DEFAULT '',
                context_version TEXT NOT NULL DEFAULT '',
                prompt_version TEXT NOT NULL DEFAULT '',
                model_version TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (project_id, paper_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_project_papers_status ON project_papers(project_id, status)",
            """
            CREATE TABLE IF NOT EXISTS search_intents (
                intent_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                type TEXT NOT NULL,
                summary TEXT NOT NULL,
                query_terms_json TEXT NOT NULL DEFAULT '[]',
                expected_evidence_types_json TEXT NOT NULL DEFAULT '[]',
                related_rq_ids_json TEXT NOT NULL DEFAULT '[]',
                related_milestone_ids_json TEXT NOT NULL DEFAULT '[]',
                related_risk_ids_json TEXT NOT NULL DEFAULT '[]',
                priority INTEGER NOT NULL DEFAULT 50,
                source_refs_json TEXT NOT NULL DEFAULT '[]',
                context_version TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'proposed',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_search_intents_project ON search_intents(project_id, status, priority DESC)",
            """
            CREATE TABLE IF NOT EXISTS search_runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                job_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                context_version TEXT NOT NULL DEFAULT '',
                context_json TEXT NOT NULL DEFAULT '{}',
                queries_json TEXT NOT NULL DEFAULT '[]',
                suggestions_json TEXT NOT NULL DEFAULT '[]',
                stats_json TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                started_at REAL NOT NULL,
                finished_at REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_search_runs_project ON search_runs(project_id, created_at DESC)",
            """
            CREATE TABLE IF NOT EXISTS search_run_candidates (
                run_id TEXT NOT NULL REFERENCES search_runs(run_id) ON DELETE CASCADE,
                project_id TEXT NOT NULL,
                paper_key TEXT NOT NULL REFERENCES papers(paper_key) ON DELETE CASCADE,
                rank INTEGER NOT NULL,
                link_json TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (run_id, paper_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_search_run_candidates_project ON search_run_candidates(project_id, run_id, rank)",
            """
            CREATE TABLE IF NOT EXISTS legacy_imports (
                source_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                imported_at REAL NOT NULL,
                summary_json TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (source_path, content_hash)
            )
            """,
        ],
    ),
    (
        "0004_p2_run_intents",
        [
            """
            CREATE TABLE IF NOT EXISTS search_run_intents (
                run_id TEXT NOT NULL REFERENCES search_runs(run_id) ON DELETE CASCADE,
                intent_id TEXT NOT NULL REFERENCES search_intents(intent_id) ON DELETE CASCADE,
                rank INTEGER NOT NULL,
                PRIMARY KEY (run_id, intent_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_search_run_intents_run ON search_run_intents(run_id, rank)",
        ],
    ),
    (
        "0005_evidence_ledger",
        [
            """
            CREATE TABLE IF NOT EXISTS source_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                source_identity TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                publisher TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                retrieved_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'available',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                UNIQUE(source_identity, content_hash)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_source_snapshots_identity ON source_snapshots(source_identity, created_at DESC)",
            """
            CREATE TABLE IF NOT EXISTS ledger_evidence_items (
                evidence_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                source_snapshot_id TEXT NOT NULL REFERENCES source_snapshots(snapshot_id),
                subquestion_id TEXT NOT NULL DEFAULT '',
                query_id TEXT NOT NULL DEFAULT '',
                evidence_type TEXT NOT NULL DEFAULT '',
                relationship TEXT NOT NULL DEFAULT 'supports',
                visibility TEXT NOT NULL DEFAULT 'primary',
                claim_text TEXT NOT NULL DEFAULT '',
                quote TEXT NOT NULL DEFAULT '',
                locator_json TEXT NOT NULL DEFAULT '{}',
                limitations_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ledger_evidence_run ON ledger_evidence_items(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_evidence_source ON ledger_evidence_items(source_snapshot_id)",
            """
            CREATE TABLE IF NOT EXISTS ledger_claims (
                claim_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                subquestion_id TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL,
                claim_type TEXT NOT NULL DEFAULT 'model_analysis',
                importance TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'uncertain',
                confidence REAL NOT NULL DEFAULT 0,
                verification_json TEXT NOT NULL DEFAULT '{}',
                generation_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ledger_claims_run ON ledger_claims(run_id)",
            """
            CREATE TABLE IF NOT EXISTS evidence_relations (
                relation_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                UNIQUE(source_kind, source_id, target_kind, target_id, relation_type)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_evidence_relations_source ON evidence_relations(source_kind, source_id)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_relations_target ON evidence_relations(target_kind, target_id)",
            """
            CREATE TABLE IF NOT EXISTS ledger_transformations (
                transformation_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                output_hash TEXT NOT NULL,
                input_refs_json TEXT NOT NULL DEFAULT '[]',
                output_refs_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ledger_transformations_run ON ledger_transformations(run_id, created_at)",
            """
            CREATE TABLE IF NOT EXISTS ledger_artifact_claims (
                artifact_id TEXT NOT NULL,
                claim_id TEXT NOT NULL REFERENCES ledger_claims(claim_id),
                artifact_type TEXT NOT NULL DEFAULT 'report',
                project_id TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                PRIMARY KEY (artifact_id, claim_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ledger_artifact_claims_claim ON ledger_artifact_claims(claim_id)",
            """
            CREATE TABLE IF NOT EXISTS evidence_review_runs (
                review_id TEXT PRIMARY KEY,
                source_identity TEXT NOT NULL,
                prior_snapshot_id TEXT NOT NULL DEFAULT '',
                current_snapshot_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT NOT NULL DEFAULT '',
                requested_by_run_id TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_evidence_review_status ON evidence_review_runs(status, created_at DESC)",
            """
            CREATE TABLE IF NOT EXISTS evidence_review_impacts (
                review_id TEXT NOT NULL REFERENCES evidence_review_runs(review_id) ON DELETE CASCADE,
                target_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                project_id TEXT NOT NULL DEFAULT '',
                impact_type TEXT NOT NULL DEFAULT 'source_changed',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (review_id, target_kind, target_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_evidence_review_impacts_target ON evidence_review_impacts(target_kind, target_id)",
        ],
    ),
    (
        "0006_retrieval_cursors",
        [
            """
            CREATE TABLE IF NOT EXISTS retrieval_cursors (
                profile_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                last_retrieved_at REAL NOT NULL,
                last_run_id TEXT NOT NULL DEFAULT '',
                last_year_from INTEGER,
                last_year_to INTEGER,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (profile_id, track_id, tier)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_retrieval_cursors_profile ON retrieval_cursors(profile_id, last_retrieved_at)",
        ],
    ),
]


def _json_dumps(value: Any) -> str:
    return json.dumps(_json_value(value), ensure_ascii=False, default=str)


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def _text_value(value: Any, default: str = "") -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value if value not in (None, "") else default)


def _json_loads(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class SQLiteDatabase:
    """Thin connection wrapper with schema bootstrap helpers."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> "SQLiteDatabase":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        self._connection = connection
        return self

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self.connect()
        assert self._connection is not None
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "SQLiteDatabase":
        return self.connect()

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def schema_version(self) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS n FROM schema_migrations"
        ).fetchone()
        return int(row["n"]) if row else 0

    def pending_migrations(self) -> list[tuple[str, list[str]]]:
        applied = {
            str(row["version"])
            for row in self.connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        }
        return [(version, statements) for version, statements in SCHEMA_MIGRATIONS if version not in applied]

    def apply_migrations(self) -> int:
        pending = self.pending_migrations()
        if not pending:
            return 0
        connection = self.connection
        connection.execute("BEGIN")
        try:
            for version, statements in pending:
                for statement in statements:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, time.time()),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return len(pending)

    def bootstrap_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at REAL NOT NULL
            )
            """
        )
        self.apply_migrations()


class RunStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def create_run(
        self,
        *,
        run_id: str | None = None,
        workspace: str = ".",
        status: str = "running",
        thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = run_id or uuid.uuid4().hex[:12]
        now = time.time()
        self.db.connection.execute(
            """
            INSERT INTO runs (run_id, workspace, status, thread_id, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, workspace, status, thread_id, _json_dumps(metadata or {}), now, now),
        )
        self.db.connection.commit()
        return self.get(run_id) or {}

    def update_status(self, run_id: str, status: str) -> bool:
        cursor = self.db.connection.execute(
            "UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?",
            (status, time.time(), run_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def update_metadata(
        self,
        run_id: str,
        metadata: dict[str, Any],
        *,
        status: str | None = None,
    ) -> bool:
        current = self.get(run_id)
        if current is None:
            return False
        merged = dict(current.get("metadata") or {})
        merged.update(metadata)
        next_status = str(status or current.get("status") or "running")
        cursor = self.db.connection.execute(
            "UPDATE runs SET status = ?, metadata_json = ?, updated_at = ? WHERE run_id = ?",
            (next_status, _json_dumps(merged), time.time(), run_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def get(self, run_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        result = _row_to_dict(row)
        result["metadata"] = _json_loads(result.pop("metadata_json", None), {})
        return result

    def list(self, *, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if status is None:
            rows = self.db.connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM runs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = _row_to_dict(row)
            item["metadata"] = _json_loads(item.pop("metadata_json", None), {})
            result.append(item)
        return result

    def add_step(
        self,
        run_id: str,
        step: StepResult | dict[str, Any],
        *,
        step_id: str | None = None,
        seq: int | None = None,
    ) -> dict[str, Any]:
        payload = step.model_dump() if isinstance(step, StepResult) else dict(step)
        step_id = step_id or str(payload.get("id") or uuid.uuid4().hex[:16])
        last = self.last_step(run_id)
        seq = seq if seq is not None else int((last or {}).get("seq", 0)) + 1
        now = time.time()
        self.db.connection.execute(
            """
            INSERT INTO run_steps (
                step_id, run_id, seq, plugin_id, capability_id, status,
                output_json, evidence_json, artifact_refs_json, metrics_json,
                error, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step_id,
                run_id,
                seq,
                str(payload.get("plugin_id") or ""),
                str(payload.get("capability_id") or ""),
                str(payload.get("status") or "unknown"),
                _json_dumps(payload.get("output") or {}),
                _json_dumps(payload.get("evidence_refs") or []),
                _json_dumps(payload.get("artifact_refs") or []),
                _json_dumps(payload.get("metrics") or {}),
                str(payload.get("error") or ""),
                str(payload.get("detail") or ""),
                now,
            ),
        )
        self.db.connection.commit()
        return self.get_step(step_id) or {}

    def get_step(self, step_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM run_steps WHERE step_id = ?", (step_id,)
        ).fetchone()
        if row is None:
            return None
        return self._step_row(row)

    def steps(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            "SELECT * FROM run_steps WHERE run_id = ? ORDER BY seq", (run_id,)
        ).fetchall()
        return [self._step_row(row) for row in rows]

    def last_step(self, run_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM run_steps WHERE run_id = ? ORDER BY seq DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        return self._step_row(row) if row is not None else None

    def _step_row(self, row: sqlite3.Row) -> dict[str, Any]:
        result = _row_to_dict(row)
        result["output"] = _json_loads(result.pop("output_json", None), {})
        result["evidence_refs"] = _json_loads(result.pop("evidence_json", None), [])
        result["artifact_refs"] = _json_loads(result.pop("artifact_refs_json", None), [])
        result["metrics"] = _json_loads(result.pop("metrics_json", None), {})
        return result


class EventStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def append(self, event: Any) -> int:
        payload = _event_payload(event)
        run_id = str(payload.get("run_id") or "")
        thread_id = str(payload.get("thread_id") or "")
        cursor = self.db.connection.execute(
            """
            INSERT INTO run_events (
                run_id, thread_id, stage, status, source, summary,
                metadata_json, elapsed_ms, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                thread_id,
                str(payload.get("stage") or "unknown"),
                str(payload.get("status") or "unknown"),
                payload.get("source"),
                str(payload.get("summary") or ""),
                _json_dumps(payload.get("metadata") or {}),
                float(payload.get("elapsed_ms") or 0.0),
                float(payload.get("timestamp") or time.time()),
            ),
        )
        self.db.connection.commit()
        return int(cursor.lastrowid)

    def list(
        self,
        *,
        run_id: str | None = None,
        after_id: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if after_id is not None:
            clauses.append("event_id > ?")
            params.append(after_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self.db.connection.execute(
            f"SELECT * FROM run_events {where} ORDER BY event_id LIMIT ?", params
        ).fetchall()
        result = []
        for row in rows:
            item = _row_to_dict(row)
            item["metadata"] = _json_loads(item.pop("metadata_json", None), {})
            result.append(item)
        return result


class ApprovalStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def create(
        self,
        approval: ApprovalRequest | dict[str, Any],
        *,
        run_id: str = "",
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        payload = approval.model_dump() if isinstance(approval, ApprovalRequest) else dict(approval)
        approval_id = approval_id or uuid.uuid4().hex[:16]
        now = time.time()
        self.db.connection.execute(
            """
            INSERT INTO approvals (
                approval_id, run_id, operation, diff_json, risk, input_hash,
                result, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                run_id,
                str(payload.get("operation") or ""),
                _json_dumps(payload.get("diff") or {}),
                str(payload.get("risk") or "low"),
                str(payload.get("input_hash") or ""),
                str(payload.get("result") or "pending"),
                now,
                now,
            ),
        )
        self.db.connection.commit()
        return self.get(approval_id) or {}

    def update_result(self, approval_id: str, result: str) -> bool:
        cursor = self.db.connection.execute(
            "UPDATE approvals SET result = ?, updated_at = ? WHERE approval_id = ?",
            (result, time.time(), approval_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def get(self, approval_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()
        if row is None:
            return None
        result = _row_to_dict(row)
        result["diff"] = _json_loads(result.pop("diff_json", None), {})
        return result

    def list(self, *, result: str | None = None) -> list[dict[str, Any]]:
        if result is None:
            rows = self.db.connection.execute(
                "SELECT * FROM approvals ORDER BY created_at"
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM approvals WHERE result = ? ORDER BY created_at", (result,)
            ).fetchall()
        items = []
        for row in rows:
            item = _row_to_dict(row)
            item["diff"] = _json_loads(item.pop("diff_json", None), {})
            items.append(item)
        return items


class ArtifactStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def register(self, artifact: ArtifactRef | dict[str, Any]) -> dict[str, Any]:
        payload = artifact.model_dump() if isinstance(artifact, ArtifactRef) else dict(artifact)
        artifact_id = str(payload.get("id") or uuid.uuid4().hex[:16])
        self.db.connection.execute(
            """
            INSERT INTO artifacts (
                artifact_id, type, content_hash, location, source_run_id, source_step_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                str(payload.get("type") or ""),
                str(payload.get("hash") or ""),
                str(payload.get("location") or ""),
                str(payload.get("source_run_id") or ""),
                str(payload.get("source_step_id") or ""),
                time.time(),
            ),
        )
        self.db.connection.commit()
        return self.get(artifact_id) or {}

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return _row_to_dict(row) if row is not None else None

    def list(self, *, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            rows = self.db.connection.execute(
                "SELECT * FROM artifacts ORDER BY created_at"
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM artifacts WHERE source_run_id = ? ORDER BY created_at",
                (run_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]


def _model_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("value must be a dict, pydantic model, or dataclass")


def _paper_key(identity: dict[str, Any]) -> str:
    doi = str(identity.get("doi") or "").strip().casefold()
    if doi:
        return f"doi:{doi}"
    source = str(identity.get("source") or "unknown").strip().casefold()
    canonical_id = str(identity.get("canonical_id") or identity.get("id") or "").strip()
    if not canonical_id:
        raise ValueError("paper identity requires canonical_id")
    return f"{source}:{canonical_id}"


class PaperStore:
    """Global paper identity repository; project-specific state lives elsewhere."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def upsert(
        self,
        identity: Any,
        *,
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        payload = _model_payload(identity)
        key = _paper_key(payload)
        now = time.time()
        try:
            self.db.connection.execute(
                """
            INSERT INTO papers (
                paper_key, source, canonical_id, version, doi, title_hash,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_key) DO UPDATE SET
                source = excluded.source,
                canonical_id = excluded.canonical_id,
                version = excluded.version,
                doi = excluded.doi,
                title_hash = excluded.title_hash,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
                """,
                (
                key,
                str(payload.get("source") or "unknown"),
                str(payload.get("canonical_id") or payload.get("id") or ""),
                str(payload.get("version") or ""),
                str(payload.get("doi") or ""),
                str(payload.get("title_hash") or ""),
                _json_dumps(metadata or payload.get("metadata") or {}),
                now,
                now,
                ),
            )
            if commit:
                self.db.connection.commit()
        except Exception:
            if commit:
                self.db.connection.rollback()
            raise
        return self.get(key) or {}

    def get(self, paper_key: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM papers WHERE paper_key = ?", (paper_key,)
        ).fetchone()
        if row is None:
            return None
        item = _row_to_dict(row)
        item["metadata"] = _json_loads(item.pop("metadata_json", None), {})
        return item


class ProjectPaperStore:
    """Project-scoped paper status and relevance metadata."""

    _JSON_FIELDS = (
        "matched_intent_ids",
        "matched_track_ids",
        "matched_rq_ids",
        "matched_milestone_ids",
    )

    def __init__(self, db: SQLiteDatabase, papers: PaperStore | None = None) -> None:
        self.db = db
        self.papers = papers or PaperStore(db)

    def upsert(
        self,
        link: Any,
        *,
        preserve_status: bool = False,
        commit: bool = True,
    ) -> dict[str, Any]:
        payload = _model_payload(link)
        identity = _model_payload(payload.get("paper_identity") or {})
        try:
            paper = self.papers.upsert(identity, commit=False)
            project_id = str(payload.get("project_id") or "").strip()
            if not project_id:
                raise ValueError("project paper link requires project_id")
            status = _text_value(payload.get("status"), "discovered")
            now = time.time()
            existing = self.get(project_id, paper["paper_key"])
            if preserve_status and existing:
                status = str(existing["status"])
            self.db.connection.execute(
                """
            INSERT INTO project_papers (
                project_id, paper_key, status, matched_intent_ids_json,
                matched_track_ids_json, matched_rq_ids_json,
                matched_milestone_ids_json, evidence_utility, relevance,
                urgency, novelty, review_confidence, profile_version,
                context_version, prompt_version, model_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, paper_key) DO UPDATE SET
                status = excluded.status,
                matched_intent_ids_json = excluded.matched_intent_ids_json,
                matched_track_ids_json = excluded.matched_track_ids_json,
                matched_rq_ids_json = excluded.matched_rq_ids_json,
                matched_milestone_ids_json = excluded.matched_milestone_ids_json,
                evidence_utility = excluded.evidence_utility,
                relevance = excluded.relevance,
                urgency = excluded.urgency,
                novelty = excluded.novelty,
                review_confidence = excluded.review_confidence,
                profile_version = excluded.profile_version,
                context_version = excluded.context_version,
                prompt_version = excluded.prompt_version,
                model_version = excluded.model_version,
                updated_at = excluded.updated_at
                """,
                (
                project_id,
                paper["paper_key"],
                status,
                _json_dumps(payload.get("matched_intent_ids") or []),
                _json_dumps(payload.get("matched_track_ids") or []),
                _json_dumps(payload.get("matched_rq_ids") or []),
                _json_dumps(payload.get("matched_milestone_ids") or []),
                _text_value(payload.get("evidence_utility"), "none"),
                float(payload.get("relevance") or 0),
                float(payload.get("urgency") or 0),
                float(payload.get("novelty") or 0),
                float(payload.get("review_confidence") or 0),
                str(payload.get("profile_version") or ""),
                str(payload.get("context_version") or ""),
                str(payload.get("prompt_version") or ""),
                str(payload.get("model_version") or ""),
                now,
                now,
                ),
            )
            if commit:
                self.db.connection.commit()
        except Exception:
            if commit:
                self.db.connection.rollback()
            raise
        return self.get(project_id, paper["paper_key"]) or {}

    def update_status(self, project_id: str, paper_id: str, status: str) -> bool:
        rows = self.db.connection.execute(
            """
            SELECT pp.paper_key
            FROM project_papers pp JOIN papers p ON p.paper_key = pp.paper_key
            WHERE pp.project_id = ? AND (pp.paper_key = ? OR p.canonical_id = ?)
            """,
            (project_id, paper_id, paper_id),
        ).fetchall()
        if len(rows) != 1:
            return False
        cursor = self.db.connection.execute(
            "UPDATE project_papers SET status = ?, updated_at = ? WHERE project_id = ? AND paper_key = ?",
            (status, time.time(), project_id, str(rows[0]["paper_key"])),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def get(self, project_id: str, paper_key: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            """
            SELECT pp.*, p.source, p.canonical_id, p.version, p.doi, p.title_hash,
                   p.metadata_json
            FROM project_papers pp JOIN papers p ON p.paper_key = pp.paper_key
            WHERE pp.project_id = ? AND pp.paper_key = ?
            """,
            (project_id, paper_key),
        ).fetchone()
        return self._row(row) if row is not None else None

    def list(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            """
            SELECT pp.*, p.source, p.canonical_id, p.version, p.doi, p.title_hash,
                   p.metadata_json
            FROM project_papers pp JOIN papers p ON p.paper_key = pp.paper_key
            WHERE pp.project_id = ? ORDER BY pp.updated_at DESC
            """,
            (project_id,),
        ).fetchall()
        return [self._row(row) for row in rows]

    def seen_statuses(self, project_id: str) -> dict[str, dict[str, str]]:
        return {
            f"{item['source']}:{item['canonical_id']}": {"status": str(item["status"])}
            for item in self.list(project_id)
        }

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        item = _row_to_dict(row)
        for name in self._JSON_FIELDS:
            item[name] = _json_loads(item.pop(f"{name}_json", None), [])
        item["metadata"] = _json_loads(item.pop("metadata_json", None), {})
        item["paper_identity"] = {
            "source": item.pop("source"),
            "canonical_id": item.pop("canonical_id"),
            "version": item.pop("version"),
            "doi": item.pop("doi"),
            "title_hash": item.pop("title_hash"),
        }
        return item


class SearchIntentStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def upsert(
        self,
        intent: Any,
        *,
        preserve_status: bool = True,
        commit: bool = True,
    ) -> dict[str, Any]:
        payload = _model_payload(intent)
        intent_id = str(payload.get("id") or payload.get("intent_id") or "").strip()
        project_id = str(payload.get("project_id") or "").strip()
        if not intent_id or not project_id:
            raise ValueError("search intent requires id and project_id")
        now = time.time()
        existing = self.get(intent_id)
        status = _text_value(
            existing["status"] if preserve_status and existing else payload.get("status"),
            "proposed",
        )
        try:
            self.db.connection.execute(
                """
            INSERT INTO search_intents (
                intent_id, project_id, type, summary, query_terms_json,
                expected_evidence_types_json, related_rq_ids_json,
                related_milestone_ids_json, related_risk_ids_json, priority,
                source_refs_json, context_version, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(intent_id) DO UPDATE SET
                project_id = excluded.project_id,
                type = excluded.type,
                summary = excluded.summary,
                query_terms_json = excluded.query_terms_json,
                expected_evidence_types_json = excluded.expected_evidence_types_json,
                related_rq_ids_json = excluded.related_rq_ids_json,
                related_milestone_ids_json = excluded.related_milestone_ids_json,
                related_risk_ids_json = excluded.related_risk_ids_json,
                priority = excluded.priority,
                source_refs_json = excluded.source_refs_json,
                context_version = excluded.context_version,
                status = excluded.status,
                updated_at = excluded.updated_at
                """,
                (
                intent_id, project_id, _text_value(payload.get("type"), "core_topic"),
                str(payload.get("summary") or ""), _json_dumps(payload.get("query_terms") or []),
                _json_dumps(payload.get("expected_evidence_types") or []),
                _json_dumps(payload.get("related_rq_ids") or []),
                _json_dumps(payload.get("related_milestone_ids") or []),
                _json_dumps(payload.get("related_risk_ids") or []), int(payload.get("priority") or 50),
                _json_dumps(payload.get("source_refs") or []), str(payload.get("context_version") or ""),
                status, now, now,
                ),
            )
            if commit:
                self.db.connection.commit()
        except Exception:
            if commit:
                self.db.connection.rollback()
            raise
        return self.get(intent_id) or {}

    def get(self, intent_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM search_intents WHERE intent_id = ?", (intent_id,)
        ).fetchone()
        return self._row(row) if row is not None else None

    def list(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            "SELECT * FROM search_intents WHERE project_id = ? ORDER BY priority DESC, intent_id",
            (project_id,),
        ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        item = _row_to_dict(row)
        item["id"] = item.pop("intent_id")
        for name in (
            "query_terms", "expected_evidence_types", "related_rq_ids",
            "related_milestone_ids", "related_risk_ids", "source_refs",
        ):
            item[name] = _json_loads(item.pop(f"{name}_json", None), [])
        return item


class SearchRunStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def save_result(
        self,
        result: Any,
        *,
        job_id: str = "",
        status: str = "completed",
        commit: bool = True,
    ) -> dict[str, Any]:
        payload = _model_payload(result)
        stats = _model_payload(payload.get("stats") or {})
        run_id = str(stats.get("run_id") or payload.get("run_id") or uuid.uuid4().hex[:12])
        project_id = str(payload.get("project_id") or stats.get("project_id") or "")
        context = _model_payload(payload.get("context") or {})
        started_at = _timestamp(stats.get("started_at"), time.time())
        finished_at = _timestamp(stats.get("finished_at"), time.time())
        now = time.time()
        connection = self.db.connection
        owns_transaction = commit and not connection.in_transaction
        if owns_transaction:
            connection.execute("BEGIN")
        try:
            connection.execute(
                """
            INSERT INTO search_runs (
                run_id, project_id, job_id, status, context_version, context_json,
                queries_json, suggestions_json, stats_json, error, started_at,
                finished_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                job_id = excluded.job_id, status = excluded.status,
                context_version = excluded.context_version,
                context_json = excluded.context_json, queries_json = excluded.queries_json,
                suggestions_json = excluded.suggestions_json, stats_json = excluded.stats_json,
                finished_at = excluded.finished_at, updated_at = excluded.updated_at
                """,
                (
                run_id, project_id, job_id, status,
                str(context.get("project_revision") or ""), _json_dumps(context),
                _json_dumps(payload.get("queries") or []), _json_dumps(payload.get("suggestions") or []),
                _json_dumps(stats), started_at, finished_at, now, now,
                ),
            )
            connection.execute("DELETE FROM search_run_candidates WHERE run_id = ?", (run_id,))
            connection.execute("DELETE FROM search_run_intents WHERE run_id = ?", (run_id,))
            intent_store = SearchIntentStore(self.db)
            for rank, intent in enumerate(payload.get("intents") or [], start=1):
                intent_payload = _model_payload(intent)
                intent_payload["project_id"] = str(intent_payload.get("project_id") or project_id)
                persisted_intent = intent_store.upsert(intent_payload, commit=False)
                intent_id = str(persisted_intent.get("id") or "").strip()
                if intent_id:
                    connection.execute(
                        "INSERT INTO search_run_intents (run_id, intent_id, rank) VALUES (?, ?, ?)",
                        (run_id, intent_id, rank),
                    )
            paper_store = PaperStore(self.db)
            for rank, link in enumerate(payload.get("links") or [], start=1):
                link_payload = _model_payload(link)
                paper = paper_store.upsert(link_payload.get("paper_identity") or {}, commit=False)
                connection.execute(
                    """
                INSERT INTO search_run_candidates (run_id, project_id, paper_key, rank, link_json)
                VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, project_id, paper["paper_key"], rank, _json_dumps(link_payload)),
                )
            if commit:
                connection.commit()
        except Exception:
            if commit:
                connection.rollback()
            raise
        return self.get(run_id) or {}

    def fail(self, run_id: str, project_id: str, error: str, *, job_id: str = "") -> dict[str, Any]:
        now = time.time()
        self.db.connection.execute(
            """
            INSERT INTO search_runs (
                run_id, project_id, job_id, status, started_at, finished_at, created_at, updated_at, error
            ) VALUES (?, ?, ?, 'failed', ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET status = 'failed', error = excluded.error,
                finished_at = excluded.finished_at, updated_at = excluded.updated_at
            """,
            (run_id, project_id, job_id, now, now, now, now, error),
        )
        self.db.connection.commit()
        return self.get(run_id) or {}

    def get(self, run_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM search_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return self._row(row) if row is not None else None

    def latest(self, project_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM search_runs WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return self._row(row) if row is not None else None

    def candidates(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            "SELECT * FROM search_run_candidates WHERE run_id = ? ORDER BY rank", (run_id,)
        ).fetchall()
        candidates = []
        for row in rows:
            item = _json_loads(row["link_json"], {})
            item["paper_key"] = str(row["paper_key"])
            candidates.append(item)
        return candidates

    def intents(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            """
            SELECT si.*
            FROM search_run_intents sri
            JOIN search_intents si ON si.intent_id = sri.intent_id
            WHERE sri.run_id = ?
            ORDER BY sri.rank
            """,
            (run_id,),
        ).fetchall()
        return [SearchIntentStore._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        item = _row_to_dict(row)
        for name in ("context", "queries", "suggestions", "stats"):
            item[name] = _json_loads(item.pop(f"{name}_json", None), {} if name in {"context", "stats"} else [])
        return item


class JobQueue:
    """SQLite-backed durable job queue with leases and idempotency keys."""

    def __init__(self, db: SQLiteDatabase, *, lease_seconds: float = 60.0) -> None:
        self.db = db
        self.lease_seconds = lease_seconds

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        job_id: str | None = None,
        idempotency_key: str | None = None,
        run_id: str = "",
        priority: int = 0,
        scheduled_at: float | None = None,
        max_attempts: int = 3,
        commit: bool = True,
    ) -> dict[str, Any]:
        now = time.time()
        job_id = job_id or uuid.uuid4().hex[:16]
        scheduled_at = scheduled_at if scheduled_at is not None else now
        self.db.connection.execute(
            """
            INSERT INTO jobs (
                job_id, kind, payload_json, idempotency_key, run_id, status,
                priority, scheduled_at, attempts, max_attempts, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, 0, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO NOTHING
            """,
            (
                job_id,
                kind,
                _json_dumps(payload or {}),
                idempotency_key,
                run_id,
                priority,
                scheduled_at,
                max_attempts,
                now,
                now,
            ),
        )
        if commit:
            self.db.connection.commit()
        if idempotency_key:
            row = self.db.connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if row is not None:
                return _job_row(row)
        return self.get(job_id) or {}

    def claim(self, worker_id: str, *, kind: str | None = None) -> dict[str, Any] | None:
        """Atomically claim the next due job for one worker."""
        now = time.time()
        connection = self.db.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            params: list[Any] = [now, now]
            kind_clause = ""
            if kind:
                kind_clause = "AND kind = ?"
                params.append(kind)
            row = connection.execute(
                f"""
                SELECT * FROM jobs
                WHERE (
                    (status = 'pending' AND scheduled_at <= ? AND attempts < max_attempts)
                    OR (status = 'running' AND lease_expires_at IS NOT NULL
                        AND lease_expires_at <= ? AND attempts < max_attempts)
                )
                {kind_clause}
                ORDER BY priority DESC, scheduled_at, created_at
                LIMIT 1
                """,
                params,
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            lease_expires_at = now + self.lease_seconds
            connection.execute(
                """
                UPDATE jobs
                SET status = 'running', lease_owner = ?, lease_expires_at = ?,
                    last_heartbeat_at = ?, attempts = attempts + 1, updated_at = ?
                WHERE job_id = ?
                """,
                (worker_id, lease_expires_at, now, now, row["job_id"]),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return self.get(str(row["job_id"]))

    def expire_exhausted(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        """Mark expired leases that exhausted their attempt budget as failed."""
        now = time.time()
        connection = self.db.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            params: list[Any] = [now]
            kind_clause = ""
            if kind:
                kind_clause = "AND kind = ?"
                params.append(kind)
            rows = connection.execute(
                f"""
                SELECT * FROM jobs
                WHERE status = 'running' AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= ? AND attempts >= max_attempts
                  {kind_clause}
                ORDER BY created_at
                """,
                params,
            ).fetchall()
            if rows:
                job_ids = [str(row["job_id"]) for row in rows]
                placeholders = ",".join("?" for _ in job_ids)
                connection.execute(
                    f"""
                    UPDATE jobs
                    SET status = 'failed', lease_owner = NULL, lease_expires_at = NULL,
                        error = CASE WHEN error = '' THEN 'lease expired after max attempts' ELSE error END,
                        updated_at = ?
                    WHERE job_id IN ({placeholders})
                    """,
                    [now, *job_ids],
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return [self.get(str(row["job_id"])) or _job_row(row) for row in rows]

    def heartbeat(self, job_id: str, worker_id: str) -> bool:
        now = time.time()
        cursor = self.db.connection.execute(
            """
            UPDATE jobs
            SET lease_expires_at = ?, last_heartbeat_at = ?, updated_at = ?
            WHERE job_id = ? AND lease_owner = ? AND status = 'running'
            """,
            (now + self.lease_seconds, now, now, job_id, worker_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def complete(self, job_id: str, worker_id: str, *, result: dict[str, Any] | None = None) -> bool:
        now = time.time()
        cursor = self.db.connection.execute(
            """
            UPDATE jobs
            SET status = 'completed', lease_owner = NULL, lease_expires_at = NULL,
                error = '', result_json = ?, updated_at = ?
            WHERE job_id = ? AND lease_owner = ? AND status = 'running'
            """,
            (_json_dumps(result or {}), now, job_id, worker_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def fail(
        self,
        job_id: str,
        worker_id: str,
        error: str,
        *,
        retry_delay: float = 5.0,
        retryable: bool = True,
    ) -> bool:
        now = time.time()
        connection = self.db.connection
        connection.execute("BEGIN")
        try:
            row = connection.execute(
                "SELECT attempts, max_attempts FROM jobs WHERE job_id = ? AND lease_owner = ?",
                (job_id, worker_id),
            ).fetchone()
            if row is None:
                connection.rollback()
                return False
            attempts = int(row["attempts"])
            max_attempts = int(row["max_attempts"])
            if not retryable or attempts >= max_attempts:
                status = "failed"
                scheduled_at = now
            else:
                status = "pending"
                scheduled_at = now + max(0.0, retry_delay)
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL,
                    scheduled_at = ?, error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, scheduled_at, error, now, job_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return True

    def cancel(self, job_id: str, *, commit: bool = True) -> bool:
        cursor = self.db.connection.execute(
            """
            UPDATE jobs
            SET status = 'cancelled', lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
            WHERE job_id = ? AND status IN ('pending', 'running')
            """,
            (time.time(), job_id),
        )
        if commit:
            self.db.connection.commit()
        return cursor.rowcount > 0

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return _job_row(row) if row is not None else None

    def list(
        self,
        *,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self.db.connection.execute(
            f"SELECT * FROM jobs {where} ORDER BY priority DESC, scheduled_at LIMIT ?", params
        ).fetchall()
        return [_job_row(row) for row in rows]

    def stats(self) -> dict[str, int]:
        rows = self.db.connection.execute(
            "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
        ).fetchall()
        return {str(row["status"]): int(row["n"]) for row in rows}


class CheckpointStore:
    """SQLite-backed JSON checkpoints keyed by thread and step."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def save(self, thread_id: str, step_id: str, payload: dict[str, Any]) -> None:
        latest = self.db.connection.execute(
            "SELECT MAX(updated_at) AS value FROM checkpoints WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        previous = float(latest["value"] or 0.0) if latest is not None else 0.0
        now = max(time.time(), previous + 0.000001)
        self.db.connection.execute(
            """
            INSERT INTO checkpoints (thread_id, step_id, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(thread_id, step_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (thread_id, step_id, _json_dumps(payload), now, now),
        )
        self.db.connection.commit()

    def load(
        self, thread_id: str, step_id: str | None = None
    ) -> dict[str, Any] | None:
        if step_id is not None:
            row = self.db.connection.execute(
                "SELECT * FROM checkpoints WHERE thread_id = ? AND step_id = ?",
                (thread_id, step_id),
            ).fetchone()
        else:
            row = self.db.connection.execute(
                """
                SELECT * FROM checkpoints WHERE thread_id = ?
                ORDER BY updated_at DESC, step_id DESC LIMIT 1
                """,
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return _json_loads(row["payload_json"], {})

    def list(self, thread_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            "SELECT * FROM checkpoints WHERE thread_id = ? ORDER BY step_id",
            (thread_id,),
        ).fetchall()
        return [
            {
                "thread_id": row["thread_id"],
                "step_id": row["step_id"],
                "payload": _json_loads(row["payload_json"], {}),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def delete(self, thread_id: str, step_id: str | None = None) -> int:
        if step_id is None:
            cursor = self.db.connection.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
            )
        else:
            cursor = self.db.connection.execute(
                "DELETE FROM checkpoints WHERE thread_id = ? AND step_id = ?",
                (thread_id, step_id),
            )
        self.db.connection.commit()
        return cursor.rowcount


def _job_row(row: sqlite3.Row) -> dict[str, Any]:
    result = _row_to_dict(row)
    result["payload"] = _json_loads(result.pop("payload_json", None), {})
    result["result"] = _json_loads(result.pop("result_json", None), {})
    return result


def import_legacy_project_research(db: SQLiteDatabase, source: str | Path) -> dict[str, int]:
    """Import P2 run/latest/seen JSON files without modifying the source."""
    root = Path(source).expanduser().resolve()
    files = [root] if root.is_file() else sorted(root.rglob("*.json"))
    files.sort(key=lambda path: (
        0 if path.name.startswith("run_") else 1 if path.name == "latest.json" else 2,
        str(path),
    ))
    summary = {"files": 0, "skipped": 0, "runs": 0, "intents": 0, "papers": 0}
    intents = SearchIntentStore(db)
    project_papers = ProjectPaperStore(db)
    runs = SearchRunStore(db)
    for path in files:
        if path.name not in {"latest.json", "seen.json"} and not path.name.startswith("run_"):
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        source_path = str(path)
        exists = db.connection.execute(
            "SELECT 1 FROM legacy_imports WHERE source_path = ? AND content_hash = ?",
            (source_path, digest),
        ).fetchone()
        if exists:
            summary["skipped"] += 1
            continue
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            continue
        project_id = str(payload.get("project_id") or path.parent.parent.name).strip()
        db.connection.execute("BEGIN")
        try:
            if (path.name == "latest.json" or path.name.startswith("run_")) and project_id:
                for intent in payload.get("intents") or []:
                    item = dict(intent)
                    item["project_id"] = project_id
                    intents.upsert(item, preserve_status=False, commit=False)
                    summary["intents"] += 1
                links = []
                for link in payload.get("links") or []:
                    item = dict(link)
                    item["project_id"] = project_id
                    project_papers.upsert(item, preserve_status=False, commit=False)
                    links.append(item)
                    summary["papers"] += 1
                run_payload = dict(payload)
                run_payload["project_id"] = project_id
                run_payload["links"] = links
                stats = dict(run_payload.get("stats") or {})
                stats["run_id"] = str(stats.get("run_id") or payload.get("run_id") or f"legacy-{digest[:12]}")
                stats["project_id"] = project_id
                run_payload["stats"] = stats
                runs.save_result(run_payload, status="imported", commit=False)
                summary["runs"] += 1
            elif path.name == "seen.json" and project_id:
                for key, state in payload.items():
                    if ":" not in key or not isinstance(state, dict):
                        continue
                    source_name, canonical_id = key.split(":", 1)
                    project_papers.upsert({
                        "project_id": project_id,
                        "paper_identity": {"source": source_name, "canonical_id": canonical_id},
                        "status": str(state.get("status") or "discovered"),
                    }, preserve_status=False, commit=False)
                    summary["papers"] += 1
            db.connection.execute(
                "INSERT INTO legacy_imports (source_path, content_hash, imported_at, summary_json) VALUES (?, ?, ?, ?)",
                (source_path, digest, time.time(), _json_dumps(summary)),
            )
            db.connection.commit()
        except Exception:
            db.connection.rollback()
            raise
        summary["files"] += 1
    return summary


def _timestamp(value: Any, default: float) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return default


def _event_payload(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump()
    if is_dataclass(event):
        return asdict(event)
    raise TypeError("event must be a dict, pydantic model, or dataclass")


class RetrievalCursorStore:
    """Per (profile, track, tier) retrieval cursors for layered coverage (P2.6).

    Low-frequency tiers (milestone/classic) skip re-retrieval until the
    configured refresh window has elapsed.  Cursors are keyed by profile_id
    (not project_id): the same profile searches the same paper population
    across projects.
    """

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def get(
        self, profile_id: str, track_id: str, tier: str
    ) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            """
            SELECT * FROM retrieval_cursors
            WHERE profile_id = ? AND track_id = ? AND tier = ?
            """,
            (profile_id, track_id, tier),
        ).fetchone()
        return _row_to_dict(row) if row is not None else None

    def upsert(
        self,
        profile_id: str,
        track_id: str,
        tier: str,
        *,
        run_id: str = "",
        year_from: int | None = None,
        year_to: int | None = None,
        candidate_count: int = 0,
    ) -> None:
        now = time.time()
        self.db.connection.execute(
            """
            INSERT INTO retrieval_cursors (
                profile_id, track_id, tier, last_retrieved_at,
                last_run_id, last_year_from, last_year_to, candidate_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, track_id, tier) DO UPDATE SET
                last_retrieved_at = excluded.last_retrieved_at,
                last_run_id = excluded.last_run_id,
                last_year_from = excluded.last_year_from,
                last_year_to = excluded.last_year_to,
                candidate_count = excluded.candidate_count
            """,
            (profile_id, track_id, tier, now, run_id, year_from, year_to, candidate_count),
        )
        self.db.connection.commit()

    def should_refresh(
        self,
        profile_id: str,
        track_id: str,
        tier: str,
        refresh_days: int,
        *,
        force: bool = False,
    ) -> bool:
        """True when this tier must be retrieved on this run."""
        if force:
            return True
        if refresh_days <= 0:
            return True
        cursor = self.get(profile_id, track_id, tier)
        if cursor is None:
            return True
        elapsed_days = (time.time() - float(cursor["last_retrieved_at"])) / 86400.0
        return elapsed_days >= refresh_days

    def list(self, profile_id: str | None = None) -> list[dict[str, Any]]:
        if profile_id is None:
            rows = self.db.connection.execute(
                "SELECT * FROM retrieval_cursors ORDER BY profile_id, track_id, tier"
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM retrieval_cursors WHERE profile_id = ? ORDER BY track_id, tier",
                (profile_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def clear(self, profile_id: str | None = None) -> int:
        """Delete cursors; None clears all (resets every tier to 'never retrieved')."""
        if profile_id is None:
            cursor = self.db.connection.execute("DELETE FROM retrieval_cursors")
        else:
            cursor = self.db.connection.execute(
                "DELETE FROM retrieval_cursors WHERE profile_id = ?", (profile_id,)
            )
        self.db.connection.commit()
        return cursor.rowcount


def list_ingested_paper_keys(db: SQLiteDatabase) -> set[str]:
    """All globally-ingested paper_keys (cross-profile).  Used to exclude
    already-ingested papers from retrieval candidates (P2.6)."""
    rows = db.connection.execute("SELECT paper_key FROM papers").fetchall()
    return {str(row["paper_key"]) for row in rows}
