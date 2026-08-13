"""P3.1 application API — project state layer entry point (plan §11.5).

Provides the versioned state read/refresh surface.  The legacy `/api/projects`
overview adapter was removed with the old page in P3.6 (plan §17.2).
"""

from __future__ import annotations

from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .collectors import collect_all_events, ingest_events
from .contracts import SnapshotTrigger, new_event, EventKind
from .repository import ProjectIntelligence
from .state_builder import build_snapshot


class ProjectStateApplication:
    """Versioned project state facade for Workbench/CLI."""

    def __init__(self, intelligence: ProjectIntelligence) -> None:
        self.intelligence = intelligence

    def refresh(
        self,
        project: ProjectDefinition,
        *,
        force: bool = False,
        since: float = 0.0,
        check_remote: bool = False,
    ) -> dict[str, Any]:
        """Collect new facts, append events, build the next snapshot."""
        events = collect_all_events(project, self.intelligence.db, since=since, check_remote=check_remote)
        added = ingest_events(self.intelligence, events)
        snapshot = build_snapshot(
            self.intelligence,
            project,
            trigger=SnapshotTrigger.MANUAL if force else SnapshotTrigger.SCHEDULED,
            force=force,
        )
        return {
            "ok": True,
            "project_id": project.id,
            "revision": snapshot.revision,
            "new_events": added,
            "snapshot_id": snapshot.snapshot_id,
            "health": snapshot.health,
        }

    def state(self, project_id: str) -> dict[str, Any] | None:
        return self.intelligence.snapshots.current(project_id)

    def revisions(self, project_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self.intelligence.snapshots.list_revisions(project_id, limit=limit)

    def events(self, project_id: str, *, after_event_id: int = 0, limit: int = 500) -> list[dict[str, Any]]:
        return self.intelligence.events.list(project_id, after_event_id=after_event_id, limit=limit)

    def reviews(self, project_id: str, *, status: str | None = None) -> list[Any]:
        return self.intelligence.reviews.list(project_id, status=status)

    def documents(self, project_id: str) -> list[Any]:
        return self.intelligence.documents.list(project_id)

    def work_items(self, project_id: str) -> list[Any]:
        return self.intelligence.work_items.list(project_id)


def record_project_event(
    intelligence: ProjectIntelligence,
    project_id: str,
    kind: EventKind,
    *,
    payload: dict[str, Any] | None = None,
    dedup_key: str = "",
) -> str:
    """Programmatic event write (e.g. paper.saved after promotion)."""
    event = new_event(project_id, kind, payload=payload, dedup_key=dedup_key)
    return intelligence.events.append(event)
