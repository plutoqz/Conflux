"""Build ProjectResearchContext from ProjectDefinition + ResearchProfile + audit.

The context builder assembles stable context (goal, RQs, tracks) and dynamic
context (active milestones, next actions, risks, evidence gaps) from the project
and its configured research profile.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from conflux.core.p2_contracts import (
    EvidenceGap,
    ProjectResearchContext,
)
from conflux.project_registry.models import ProjectDefinition, ProjectPlan
from conflux.research_profile.models import ResearchProfile


def build_project_research_context(
    project: ProjectDefinition,
    profile: ResearchProfile,
    *,
    audit: dict[str, Any] | None = None,
) -> ProjectResearchContext:
    """Assemble the full runtime context for a project's paper radar run.

    Parameters
    ----------
    project: The project definition loaded from YAML.
    profile: The research profile loaded from YAML.
    audit: Optional progress audit data containing risks, gaps, and status.
    """
    audit = audit or {}

    # Compute version hashes for reproducibility
    profile_version = _hash_dict(profile.to_dict())
    project_revision = _hash_dict(_project_essential(project))

    # Stable context from profile
    research_questions = list(profile.research_questions)

    # Dynamic context from project plan
    plan: ProjectPlan = project.plan
    active_milestones = [
        m.title
        for m in plan.milestones
        if m.status in ("in_progress", "blocked")
    ]
    next_actions = list(plan.next_actions)

    # Risks from audit
    current_risks: list[str] = []
    for risk in audit.get("risks") or []:
        if isinstance(risk, dict):
            desc = str(risk.get("description") or risk.get("title") or "")
            if desc:
                current_risks.append(desc)
        elif isinstance(risk, str):
            current_risks.append(risk)

    # Evidence gaps from audit
    evidence_gaps: list[EvidenceGap] = []
    for i, gap in enumerate(audit.get("evidence_gaps") or []):
        if isinstance(gap, dict):
            evidence_gaps.append(EvidenceGap(
                id=gap.get("id") or f"gap-{i}",
                description=str(gap.get("description") or ""),
                related_rq_ids=_str_list(gap.get("related_rq_ids")),
                related_milestone_ids=_str_list(gap.get("related_milestone_ids")),
                severity=gap.get("severity") or "medium",
            ))

    # Source refs
    source_refs: list[str] = []
    if project.source_file:
        source_refs.append(project.source_file)
    source_refs.extend(plan.source_documents)

    return ProjectResearchContext(
        project_id=project.id,
        project_revision=project_revision,
        profile_id=profile.id,
        profile_version=profile_version,
        overall_goal=plan.overall_goal,
        research_questions=research_questions,
        active_milestones=active_milestones,
        next_actions=next_actions,
        current_risks=current_risks,
        evidence_gaps=evidence_gaps,
        source_refs=source_refs,
    )


def _project_essential(project: ProjectDefinition) -> dict[str, Any]:
    """Extract the version-relevant subset of a project definition."""
    return {
        "id": project.id,
        "overall_goal": project.plan.overall_goal,
        "milestones": [
            {"id": m.id, "title": m.title, "status": m.status}
            for m in project.plan.milestones
        ],
        "next_actions": project.plan.next_actions,
    }


def _hash_dict(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON-encoded dict."""
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return []
