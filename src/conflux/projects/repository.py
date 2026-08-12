"""P3 project intelligence — SQLite migration 0007 and repositories (P3.1).

Storage layer for the versioned project state: project_documents,
project_work_items, project_events, project_snapshots, project_current_state,
project_reviews, project_review_impacts, project_discovery_cursors.

Design rules from P3 §5/§9:
- YAML stays the authority for declared state; SQLite stores observed facts,
  events, inferred suggestions and review state (no second write source).
- Events are append-only and idempotent (dedup_key); snapshots are immutable;
  current state is a materialized view.
- JSON columns let contracts evolve without schema churn (M3 pattern).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from conflux.adapters.sqlite_store import SQLiteDatabase

from .contracts import (
    P3_PROTOCOL_VERSION,
    EventKind,
    ProjectContextSnapshot,
    ProjectDocument,
    ProjectEvent,
    ResearchWorkItem,
    ReviewItem,
    ReviewStatus,
)

# Migration appended to SCHEMA_MIGRATIONS by conflux.migrations.register.
# The statements below are also exposed for tests / fresh installs.
PROJECT_INTELLIGENCE_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS project_documents (
        document_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        path TEXT NOT NULL,
        content_hash TEXT NOT NULL DEFAULT '',
        kind TEXT NOT NULL DEFAULT 'other',
        authority TEXT NOT NULL DEFAULT 'candidate',
        parse_status TEXT NOT NULL DEFAULT 'pending',
        language TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        modified_at REAL NOT NULL DEFAULT 0,
        indexed_at REAL NOT NULL DEFAULT 0,
        extractor_version TEXT NOT NULL DEFAULT '',
        classification_source TEXT NOT NULL DEFAULT 'rule',
        classification_confidence REAL NOT NULL DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        UNIQUE(project_id, path)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_documents_project ON project_documents(project_id, authority)",
    """
    CREATE TABLE IF NOT EXISTS project_work_items (
        work_item_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'action',
        title TEXT NOT NULL,
        parent_id TEXT NOT NULL DEFAULT '',
        declared_status TEXT NOT NULL DEFAULT 'planned',
        observed_status TEXT NOT NULL DEFAULT 'no_evidence',
        inferred_status TEXT NOT NULL DEFAULT 'needs_review',
        acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
        source_refs_json TEXT NOT NULL DEFAULT '[]',
        evidence_refs_json TEXT NOT NULL DEFAULT '[]',
        linked_branch TEXT NOT NULL DEFAULT '',
        linked_run_ids_json TEXT NOT NULL DEFAULT '[]',
        linked_paper_keys_json TEXT NOT NULL DEFAULT '[]',
        updated_at REAL NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_work_items_project ON project_work_items(project_id)",
    """
    CREATE TABLE IF NOT EXISTS project_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at REAL NOT NULL,
        dedup_key TEXT NOT NULL DEFAULT '',
        UNIQUE(project_id, dedup_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_events_project ON project_events(project_id, event_id)",
    """
    CREATE TABLE IF NOT EXISTS project_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        revision INTEGER NOT NULL,
        created_at REAL NOT NULL,
        trigger TEXT NOT NULL DEFAULT 'initial',
        definition_version TEXT NOT NULL DEFAULT '',
        document_index_version TEXT NOT NULL DEFAULT '',
        git_state_json TEXT NOT NULL DEFAULT '{}',
        work_items_json TEXT NOT NULL DEFAULT '[]',
        knowledge_state_json TEXT NOT NULL DEFAULT '{}',
        research_state_json TEXT NOT NULL DEFAULT '{}',
        run_state_json TEXT NOT NULL DEFAULT '{}',
        evidence_state_json TEXT NOT NULL DEFAULT '{}',
        health TEXT NOT NULL DEFAULT 'ok',
        summary_json TEXT NOT NULL DEFAULT '{}',
        UNIQUE(project_id, revision)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_snapshots_project ON project_snapshots(project_id, revision)",
    """
    CREATE TABLE IF NOT EXISTS project_current_state (
        project_id TEXT PRIMARY KEY,
        snapshot_id TEXT NOT NULL,
        revision INTEGER NOT NULL,
        state_json TEXT NOT NULL DEFAULT '{}',
        updated_at REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_reviews (
        review_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        priority INTEGER NOT NULL DEFAULT 50,
        status TEXT NOT NULL DEFAULT 'pending',
        summary TEXT NOT NULL DEFAULT '',
        impact_refs_json TEXT NOT NULL DEFAULT '[]',
        evidence_refs_json TEXT NOT NULL DEFAULT '[]',
        proposed_action TEXT NOT NULL DEFAULT '',
        input_snapshot_id TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL,
        resolved_at REAL NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_reviews_project ON project_reviews(project_id, status)",
    """
    CREATE TABLE IF NOT EXISTS project_review_impacts (
        impact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id TEXT NOT NULL REFERENCES project_reviews(review_id) ON DELETE CASCADE,
        target_kind TEXT NOT NULL,
        target_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_discovery_cursors (
        project_id TEXT PRIMARY KEY,
        last_scan_at REAL NOT NULL,
        scan_version TEXT NOT NULL DEFAULT '',
        cursor_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def register_project_intelligence_migration() -> None:
    """Append migration 0007 to the global SCHEMA_MIGRATIONS (idempotent).

    Called at import time by ``conflux.projects`` so ``conflux migrate`` and
    ``bootstrap_schema`` pick it up without schema-store edits.
    """
    from conflux.adapters import sqlite_store as store

    versions = {item[0] for item in store.SCHEMA_MIGRATIONS}
    if "0007_project_intelligence" not in versions:
        store.SCHEMA_MIGRATIONS.append(
            ("0007_project_intelligence", list(PROJECT_INTELLIGENCE_STATEMENTS))
        )


register_project_intelligence_migration()


class ProjectEventStore:
    """Append-only, idempotent event log."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def append(self, event: ProjectEvent) -> str:
        dedup = event.dedup_key or f"auto-{uuid.uuid4().hex[:16]}"
        try:
            cursor = self.db.connection.execute(
                """
                INSERT INTO project_events (project_id, kind, payload_json, created_at, dedup_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event.project_id, event.kind.value, _json_dumps(event.payload),
                 event.created_at or time.time(), dedup),
            )
            self.db.connection.commit()
            return str(cursor.lastrowid)
        except Exception:
            # Unique(project_id, dedup_key) violation => already applied.
            self.db.connection.rollback()
            return ""

    def list(self, project_id: str, *, after_event_id: int = 0, limit: int = 500) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            """
            SELECT * FROM project_events
            WHERE project_id = ? AND event_id > ?
            ORDER BY event_id ASC LIMIT ?
            """,
            (project_id, after_event_id, limit),
        ).fetchall()
        return [_event_row(row) for row in rows]

    def count(self, project_id: str) -> int:
        row = self.db.connection.execute(
            "SELECT COUNT(*) AS n FROM project_events WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return int(row["n"]) if row else 0


def _event_row(row: Any) -> dict[str, Any]:
    return {
        "event_id": int(row["event_id"]),
        "project_id": str(row["project_id"]),
        "kind": str(row["kind"]),
        "payload": _json_loads(row["payload_json"], {}),
        "created_at": float(row["created_at"]),
        "dedup_key": str(row["dedup_key"]),
    }


class ProjectSnapshotStore:
    """Immutable snapshots + materialized current state."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def save(self, snapshot: ProjectContextSnapshot) -> None:
        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO project_snapshots (
                snapshot_id, project_id, revision, created_at, trigger,
                definition_version, document_index_version, git_state_json,
                work_items_json, knowledge_state_json, research_state_json,
                run_state_json, evidence_state_json, health, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.snapshot_id, snapshot.project_id, snapshot.revision,
                snapshot.created_at, snapshot.trigger.value,
                snapshot.definition_version, snapshot.document_index_version,
                _json_dumps(snapshot.git_state.model_dump()),
                _json_dumps(snapshot.work_items),
                _json_dumps(snapshot.knowledge_state),
                _json_dumps(snapshot.research_state),
                _json_dumps(snapshot.run_state),
                _json_dumps(snapshot.evidence_state),
                snapshot.health, _json_dumps(snapshot.summary),
            ),
        )
        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO project_current_state (
                project_id, snapshot_id, revision, state_json, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot.project_id, snapshot.snapshot_id, snapshot.revision,
                _json_dumps(snapshot.model_dump()), time.time(),
            ),
        )
        self.db.connection.commit()

    def latest(self, project_id: str) -> ProjectContextSnapshot | None:
        row = self.db.connection.execute(
            "SELECT * FROM project_snapshots WHERE project_id = ? ORDER BY revision DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return _snapshot_from_row(row) if row else None

    def get(self, project_id: str, revision: int) -> ProjectContextSnapshot | None:
        row = self.db.connection.execute(
            "SELECT * FROM project_snapshots WHERE project_id = ? AND revision = ?",
            (project_id, revision),
        ).fetchone()
        return _snapshot_from_row(row) if row else None

    def current(self, project_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM project_current_state WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if not row:
            return None
        state = _json_loads(row["state_json"], {})
        state["snapshot_id"] = str(row["snapshot_id"])
        state["revision"] = int(row["revision"])
        state["updated_at"] = float(row["updated_at"])
        return state

    def list_revisions(self, project_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            """
            SELECT snapshot_id, revision, created_at, trigger, health
            FROM project_snapshots WHERE project_id = ?
            ORDER BY revision DESC LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def _snapshot_from_row(row: Any) -> ProjectContextSnapshot:
    return ProjectContextSnapshot(
        snapshot_id=str(row["snapshot_id"]),
        project_id=str(row["project_id"]),
        revision=int(row["revision"]),
        created_at=float(row["created_at"]),
        trigger=row["trigger"],
        definition_version=str(row["definition_version"]),
        document_index_version=str(row["document_index_version"]),
        git_state=_json_loads(row["git_state_json"], {}),
        work_items=_json_loads(row["work_items_json"], []),
        knowledge_state=_json_loads(row["knowledge_state_json"], {}),
        research_state=_json_loads(row["research_state_json"], {}),
        run_state=_json_loads(row["run_state_json"], {}),
        evidence_state=_json_loads(row["evidence_state_json"], {}),
        health=str(row["health"]),
        summary=_json_loads(row["summary_json"], {}),
    )


class ProjectDocumentStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def upsert(self, document: ProjectDocument) -> None:
        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO project_documents (
                document_id, project_id, path, content_hash, kind, authority,
                parse_status, language, title, modified_at, indexed_at,
                extractor_version, classification_source, classification_confidence,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.document_id, document.project_id, document.path,
                document.content_hash, document.kind.value, document.authority.value,
                document.parse_status.value, document.language, document.title,
                document.modified_at, document.indexed_at, document.extractor_version,
                document.classification_source.value, document.classification_confidence,
                _json_dumps(document.metadata),
            ),
        )
        self.db.connection.commit()

    def list(self, project_id: str) -> list[ProjectDocument]:
        rows = self.db.connection.execute(
            "SELECT * FROM project_documents WHERE project_id = ? ORDER BY path",
            (project_id,),
        ).fetchall()
        return [_document_from_row(row) for row in rows]

    def get(self, document_id: str) -> ProjectDocument | None:
        row = self.db.connection.execute(
            "SELECT * FROM project_documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        return _document_from_row(row) if row else None

    def set_authority(self, document_id: str, authority: str) -> bool:
        cursor = self.db.connection.execute(
            "UPDATE project_documents SET authority = ? WHERE document_id = ?",
            (authority, document_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0


def _document_from_row(row: Any) -> ProjectDocument:
    return ProjectDocument(
        document_id=str(row["document_id"]),
        project_id=str(row["project_id"]),
        path=str(row["path"]),
        content_hash=str(row["content_hash"]),
        kind=row["kind"],
        authority=row["authority"],
        parse_status=row["parse_status"],
        language=str(row["language"]),
        title=str(row["title"]),
        modified_at=float(row["modified_at"]),
        indexed_at=float(row["indexed_at"]),
        extractor_version=str(row["extractor_version"]),
        classification_source=row["classification_source"],
        classification_confidence=float(row["classification_confidence"]),
        metadata=_json_loads(row["metadata_json"], {}),
    )


class ProjectWorkItemStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def upsert(self, item: ResearchWorkItem) -> None:
        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO project_work_items (
                work_item_id, project_id, kind, title, parent_id,
                declared_status, observed_status, inferred_status,
                acceptance_criteria_json, source_refs_json, evidence_refs_json,
                linked_branch, linked_run_ids_json, linked_paper_keys_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.work_item_id, item.project_id, item.kind.value, item.title,
                item.parent_id, item.declared_status.value, item.observed_status.value,
                item.inferred_status.value,
                _json_dumps(item.acceptance_criteria), _json_dumps(item.source_refs),
                _json_dumps(item.evidence_refs), item.linked_branch,
                _json_dumps(item.linked_run_ids), _json_dumps(item.linked_paper_keys),
                item.updated_at or time.time(),
            ),
        )
        self.db.connection.commit()

    def list(self, project_id: str) -> list[ResearchWorkItem]:
        rows = self.db.connection.execute(
            "SELECT * FROM project_work_items WHERE project_id = ? ORDER BY kind, title",
            (project_id,),
        ).fetchall()
        return [_work_item_from_row(row) for row in rows]

    def get(self, work_item_id: str) -> ResearchWorkItem | None:
        row = self.db.connection.execute(
            "SELECT * FROM project_work_items WHERE work_item_id = ?", (work_item_id,)
        ).fetchone()
        return _work_item_from_row(row) if row else None


def _work_item_from_row(row: Any) -> ResearchWorkItem:
    return ResearchWorkItem(
        work_item_id=str(row["work_item_id"]),
        project_id=str(row["project_id"]),
        kind=row["kind"],
        title=str(row["title"]),
        parent_id=str(row["parent_id"]),
        declared_status=row["declared_status"],
        observed_status=row["observed_status"],
        inferred_status=row["inferred_status"],
        acceptance_criteria=_json_loads(row["acceptance_criteria_json"], []),
        source_refs=_json_loads(row["source_refs_json"], []),
        evidence_refs=_json_loads(row["evidence_refs_json"], []),
        linked_branch=str(row["linked_branch"]),
        linked_run_ids=_json_loads(row["linked_run_ids_json"], []),
        linked_paper_keys=_json_loads(row["linked_paper_keys_json"], []),
        updated_at=float(row["updated_at"]),
    )


class ProjectReviewStore:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def create(self, review: ReviewItem) -> None:
        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO project_reviews (
                review_id, project_id, kind, priority, status, summary,
                impact_refs_json, evidence_refs_json, proposed_action,
                input_snapshot_id, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.review_id, review.project_id, review.kind.value,
                review.priority, review.status.value, review.summary,
                _json_dumps(review.impact_refs), _json_dumps(review.evidence_refs),
                review.proposed_action, review.input_snapshot_id,
                review.created_at or time.time(), review.resolved_at,
            ),
        )
        self.db.connection.commit()

    def list(self, project_id: str, *, status: str | None = None) -> list[ReviewItem]:
        if status is None:
            rows = self.db.connection.execute(
                "SELECT * FROM project_reviews WHERE project_id = ? ORDER BY priority DESC, created_at",
                (project_id,),
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM project_reviews WHERE project_id = ? AND status = ? ORDER BY priority DESC, created_at",
                (project_id, status),
            ).fetchall()
        return [_review_from_row(row) for row in rows]

    def resolve(self, review_id: str, result: str) -> bool:
        cursor = self.db.connection.execute(
            "UPDATE project_reviews SET status = ?, resolved_at = ? WHERE review_id = ?",
            (result, time.time(), review_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0


def _review_from_row(row: Any) -> ReviewItem:
    return ReviewItem(
        review_id=str(row["review_id"]),
        project_id=str(row["project_id"]),
        kind=row["kind"],
        priority=int(row["priority"]),
        status=row["status"],
        summary=str(row["summary"]),
        impact_refs=_json_loads(row["impact_refs_json"], []),
        evidence_refs=_json_loads(row["evidence_refs_json"], []),
        proposed_action=str(row["proposed_action"]),
        input_snapshot_id=str(row["input_snapshot_id"]),
        created_at=float(row["created_at"]),
        resolved_at=float(row["resolved_at"]),
    )


class ProjectIntelligence:
    """Facade over the P3.1 stores; one entry point for the Application API."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db
        self.events = ProjectEventStore(db)
        self.snapshots = ProjectSnapshotStore(db)
        self.documents = ProjectDocumentStore(db)
        self.work_items = ProjectWorkItemStore(db)
        self.reviews = ProjectReviewStore(db)
        self.protocol_version = P3_PROTOCOL_VERSION

    def ensure_schema(self) -> None:
        for statement in PROJECT_INTELLIGENCE_STATEMENTS:
            self.db.connection.execute(statement)
        self.db.connection.commit()
