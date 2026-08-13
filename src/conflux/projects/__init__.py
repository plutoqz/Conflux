"""P3 project intelligence package (plan §11.1).

P3.0: versioned protocol contracts (contracts.py).
P3.1: SQLite repositories + event collectors + state builder + Application
API with legacy adapter.  UI work is out of scope until P3.3.
"""

from __future__ import annotations

from .application import (
    ProjectStateApplication,
    legacy_overview_adapter,
    record_project_event,
)
from .collectors import collect_all_events, ingest_events
from .contracts import (
    P3_PROTOCOL_VERSION,
    DeclaredStatus,
    DocumentAuthority,
    DocumentKind,
    EventKind,
    InferredStatus,
    ObservedStatus,
    ProjectContextSnapshot,
    ProjectDocument,
    ProjectEvent,
    ResearchWorkItem,
    ReviewItem,
    ReviewKind,
    ReviewStatus,
    SnapshotTrigger,
    WorkItemKind,
    new_event,
    new_snapshot,
)
from .repository import (
    PROJECT_INTELLIGENCE_STATEMENTS,
    ProjectDocumentStore,
    ProjectEventStore,
    ProjectIntelligence,
    ProjectReviewStore,
    ProjectSnapshotStore,
    ProjectWorkItemStore,
    register_project_intelligence_migration,
)
from .projections import (
    knowledge_state,
    parse_work_item_ref,
    work_item_projection,
)
from .review_service import seed_reviews, supersede_document_reviews
from .state_builder import build_snapshot

__all__ = [
    "P3_PROTOCOL_VERSION",
    "DeclaredStatus",
    "DocumentAuthority",
    "DocumentKind",
    "EventKind",
    "InferredStatus",
    "ObservedStatus",
    "PROJECT_INTELLIGENCE_STATEMENTS",
    "ProjectContextSnapshot",
    "ProjectDocument",
    "ProjectDocumentStore",
    "ProjectEvent",
    "ProjectEventStore",
    "ProjectIntelligence",
    "ProjectReviewStore",
    "ProjectSnapshotStore",
    "ProjectStateApplication",
    "ProjectWorkItemStore",
    "ResearchWorkItem",
    "ReviewItem",
    "ReviewKind",
    "ReviewStatus",
    "SnapshotTrigger",
    "WorkItemKind",
    "build_snapshot",
    "collect_all_events",
    "ingest_events",
    "knowledge_state",
    "legacy_overview_adapter",
    "new_event",
    "new_snapshot",
    "parse_work_item_ref",
    "record_project_event",
    "register_project_intelligence_migration",
    "seed_reviews",
    "supersede_document_reviews",
    "work_item_projection",
]