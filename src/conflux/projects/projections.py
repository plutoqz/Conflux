"""P3.3 deterministic projections — plan -> work items, knowledge state.

Everything here is bounded and deterministic (plan §9.3): declared facts come
from the project YAML (the authority), observed counts come from SQLite, and
inferred values only use rules that never invent progress.  No model calls,
no remote checks, no directory scans — page reads stay fast.
"""

from __future__ import annotations

import time
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .repository import ProjectIntelligence

# --- work item identity -------------------------------------------------

_WI_PREFIX = ":wi:"


def goal_item_id(project_id: str) -> str:
    return f"{project_id}{_WI_PREFIX}goal"


def milestone_item_id(project_id: str, index: int) -> str:
    return f"{project_id}{_WI_PREFIX}ms-{index}"


def action_item_id(project_id: str, index: int) -> str:
    return f"{project_id}{_WI_PREFIX}act-{index}"


def parse_work_item_ref(project_id: str, work_item_id: str) -> tuple[str, int] | None:
    """Split a projection id back into (kind, index); kind in goal/ms/act."""
    prefix = f"{project_id}{_WI_PREFIX}"
    if not work_item_id.startswith(prefix):
        return None
    ref = work_item_id[len(prefix):]
    if ref == "goal":
        return ("goal", 0)
    for kind in ("ms", "act"):
        if ref.startswith(f"{kind}-"):
            try:
                return (kind, int(ref[len(kind) + 1:]))
            except ValueError:
                return None
    return None


# --- work items ---------------------------------------------------------


def _work_item(
    *,
    work_item_id: str,
    project_id: str,
    kind: str,
    title: str,
    declared_status: str,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    # Bounded rules (plan §9.3): evidence linking arrives with P3.4, so
    # observed stays no_evidence; inferred mirrors the declaration except for
    # completed (needs evidence review) and blocked (rule-confirmed).
    inferred = (
        "blocked"
        if declared_status == "blocked"
        else "needs_review"
        if declared_status == "completed"
        else declared_status
    )
    return {
        "work_item_id": work_item_id,
        "project_id": project_id,
        "kind": kind,
        "title": title,
        "parent_id": "",
        "declared_status": declared_status,
        "observed_status": "no_evidence",
        "inferred_status": inferred,
        "acceptance_criteria": list(acceptance_criteria or []),
        "source_refs": [f"projects/{project_id}.yaml"],
        "evidence_refs": [],
        "linked_branch": "",
        "linked_run_ids": [],
        "linked_paper_keys": [],
        "updated_at": time.time(),
    }


def work_item_projection(project: ProjectDefinition) -> list[dict[str, Any]]:
    """Deterministic projection of the YAML plan into work items (P3 §5.3).

    YAML remains the authority for declared status; this only mirrors it.
    """
    items: list[dict[str, Any]] = []
    if project.plan.overall_goal:
        items.append(_work_item(
            work_item_id=goal_item_id(project.id),
            project_id=project.id,
            kind="research_question",
            title=project.plan.overall_goal,
            declared_status="planned",
        ))
    for index, milestone in enumerate(project.plan.milestones):
        items.append(_work_item(
            work_item_id=milestone_item_id(project.id, index),
            project_id=project.id,
            kind="milestone",
            title=milestone.title,
            declared_status=milestone.status,
            acceptance_criteria=list(milestone.deliverables),
        ))
    for index, action in enumerate(project.plan.next_actions):
        items.append(_work_item(
            work_item_id=action_item_id(project.id, index),
            project_id=project.id,
            kind="action",
            title=action,
            declared_status="planned",
        ))
    return items


# --- knowledge state ----------------------------------------------------


def knowledge_state(intelligence: ProjectIntelligence, project_id: str) -> dict[str, Any]:
    """Document index stats from SQLite only (no re-scan, plan §13.1)."""
    documents = intelligence.documents.list(project_id)
    by_kind: dict[str, int] = {}
    by_authority: dict[str, int] = {}
    parse_failed = 0
    confirmed_authority: list[str] = []
    for doc in documents:
        by_kind[doc.kind.value] = by_kind.get(doc.kind.value, 0) + 1
        by_authority[doc.authority.value] = by_authority.get(doc.authority.value, 0) + 1
        if doc.parse_status.value == "failed":
            parse_failed += 1
        if doc.authority.value == "confirmed":
            confirmed_authority.append(doc.path)
    return {
        "documents": {
            "total": len(documents),
            "by_kind": by_kind,
            "by_authority": by_authority,
            "parse_failed": parse_failed,
        },
        "confirmed_authority": confirmed_authority,
    }
