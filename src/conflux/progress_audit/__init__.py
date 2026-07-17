"""Evidence-backed progress auditing for local research projects."""

from .auditor import audit_project, create_project_snapshot
from .models import (
    ArtifactRecord,
    GitCommit,
    ProgressAuditReport,
    ProgressClaim,
    ProjectSnapshot,
    TestResult,
)
from .progress_report import ProgressArtifacts, write_progress_artifacts

__all__ = [
    "ArtifactRecord",
    "GitCommit",
    "ProgressArtifacts",
    "ProgressAuditReport",
    "ProgressClaim",
    "ProjectSnapshot",
    "TestResult",
    "audit_project",
    "create_project_snapshot",
    "write_progress_artifacts",
]
