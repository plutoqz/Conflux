"""P3.2 document discovery service — incremental scan pipeline.

D0 (discover_candidates) -> D1 (parse_document) -> D2 (classify_document)
-> persist -> document.discovered/changed events.

Incremental strategy (P3 §8.3): only files whose (mtime, size) changed since
the last scan are re-hashed and re-parsed; unchanged files keep their
existing identity and are never re-read.  A per-project discovery cursor
(project_discovery_cursors) records the last scan time and version.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..project_registry.models import ProjectDefinition
from .contracts import (
    ClassificationSource,
    DocumentAuthority,
    DocumentKind,
    EventKind,
    ProjectDocument,
    new_event,
)
from .discovery import (
    DEFAULT_IGNORE_PATTERNS,
    MAX_CANDIDATES_PER_SCAN,
    classify_document,
    discover_candidates,
    document_id_for,
    parse_document,
)
from .repository import ProjectIntelligence


def get_cursor(intelligence: ProjectIntelligence, project_id: str) -> dict[str, Any] | None:
    row = intelligence.db.connection.execute(
        "SELECT * FROM project_discovery_cursors WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    if not row:
        return None
    import json

    return {
        "last_scan_at": float(row["last_scan_at"]),
        "scan_version": str(row["scan_version"]),
        "cursor": json.loads(row["cursor_json"] or "{}"),
    }


def set_cursor(intelligence: ProjectIntelligence, project_id: str, cursor: dict[str, Any]) -> None:
    import json

    intelligence.db.connection.execute(
        """
        INSERT OR REPLACE INTO project_discovery_cursors (project_id, last_scan_at, scan_version, cursor_json)
        VALUES (?, ?, ?, ?)
        """,
        (project_id, time.time(), "d2-20260812", json.dumps(cursor, ensure_ascii=False, sort_keys=True)),
    )
    intelligence.db.connection.commit()


def scan_project_documents(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    force: bool = False,
    max_files: int = MAX_CANDIDATES_PER_SCAN,
) -> dict[str, Any]:
    """Incremental D0-D2 scan; returns discovery telemetry."""
    root = Path(project.path).expanduser().resolve()
    if not root.is_dir():
        return {
            "ok": False,
            "project_id": project.id,
            "error": f"project path not found: {root}",
            "scanned": 0,
            "parsed": 0,
            "changed": 0,
            "events": 0,
        }

    cursor = None if force else get_cursor(intelligence, project.id)
    last_scan = (cursor or {}).get("last_scan_at") or 0.0
    known: dict[str, str] = {}
    if cursor:
        known = {str(k): str(v) for k, v in (cursor or {}).get("cursor", {}).items()}

    candidates = discover_candidates(project, max_files=max_files)
    changed: list[ProjectDocument] = []
    new_cursor: dict[str, str] = {}
    new_documents = 0
    changed_documents = 0

    for candidate in candidates:
        relative = str(candidate["relative_path"])
        new_cursor[relative] = str(candidate["mtime"])
        previous = known.get(relative)
        if not force and previous == str(candidate["mtime"]):
            # Unchanged identity -> skip (never re-read, P3 §8.3).
            continue
        document = parse_document(
            Path(candidate["path"]),
            extractor_version="d1-20260812",
        )
        document.project_id = project.id
        document.document_id = document_id_for(project.id, relative)
        document.path = relative
        classify_document(document)
        changed.append(document)
        if previous is None:
            new_documents += 1
        else:
            changed_documents += 1

    # Persist + emit events.
    events = 0
    for document in changed:
        existing = intelligence.documents.get(document.document_id)
        intelligence.documents.upsert(document)
        if existing is None or existing.content_hash != document.content_hash:
            kind = EventKind.DOCUMENT_DISCOVERED if existing is None else EventKind.DOCUMENT_CHANGED
            intelligence.events.append(new_event(
                project.id,
                kind,
                payload={
                    "document_id": document.document_id,
                    "path": document.path,
                    "kind": document.kind.value,
                    "content_hash": document.content_hash,
                    "index_version": "d2-20260812",
                },
                dedup_key=f"doc-{document.document_id}-{document.content_hash[:12]}",
            ))
            events += 1

    set_cursor(intelligence, project.id, new_cursor)
    return {
        "ok": True,
        "project_id": project.id,
        "scanned": len(candidates),
        "parsed": len(changed),
        "new": new_documents,
        "changed": changed_documents,
        "events": events,
        "force": force,
    }


def document_map(intelligence: ProjectIntelligence, project_id: str) -> dict[str, Any]:
    """Documents grouped by authority for the Workbench document map."""
    documents = intelligence.documents.list(project_id)
    by_authority: dict[str, list[dict[str, Any]]] = {}
    for doc in documents:
        by_authority.setdefault(doc.authority.value, []).append({
            "document_id": doc.document_id,
            "path": doc.path,
            "kind": doc.kind.value,
            "title": doc.title,
            "parse_status": doc.parse_status.value,
            "confidence": doc.classification_confidence,
        })
    return {
        "project_id": project_id,
        "total": len(documents),
        "by_authority": by_authority,
    }
