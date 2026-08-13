"""P3.4 link materialization — work items <-> runs/claims/papers/branch (plan §10).

Every link is deterministic and carries its source identity (run_id,
claim_id, paper_key, intent id), so the UI can always answer "why is this
linked" without model involvement.  The project YAML stays the authority
for declared fields; this layer only fills the link/evidence side of the
work-item contract, persisted in ``project_work_items`` and merged into
snapshots by the state builder.

The frozen contract keeps ``linked_run_ids``/``linked_paper_keys`` as plain
string lists; richer run detail (status/tokens) stays in the run stores and
is joined by the activity endpoint.
"""

from __future__ import annotations

from typing import Any

from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
from conflux.adapters.sqlite_store import ProjectPaperStore, RunStore, SearchIntentStore, SearchRunStore
from conflux.project_registry.models import ProjectDefinition

from .contracts import ObservedStatus, ResearchWorkItem
from .projections import work_item_projection
from .repository import ProjectIntelligence

# Verdicts that count as negative evidence for a milestone (P3 §4.2).
_NEGATIVE_VERDICTS = {"contradicts", "insufficient"}


def intent_work_item_map(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
) -> dict[str, list[str]]:
    """Map work_item_id -> intent ids, by title/id on intent source fields.

    SearchIntent is a frozen P2 contract (no work_item_id), so we match
    deterministically: related_milestone_ids by YAML milestone id, and
    source_refs ``milestone: {title}`` / ``next_action: {title}`` /
    ``research_question: {text}`` by exact title.
    """
    try:
        intents = SearchIntentStore(intelligence.db).list(project.id)
    except Exception:
        return {}

    items = work_item_projection(project)
    by_yaml_id: dict[str, str] = {}
    for index, milestone in enumerate(project.plan.milestones):
        if milestone.id:
            by_yaml_id[milestone.id] = f"{project.id}:wi:ms-{index}"
    by_title = {item["title"]: item["work_item_id"] for item in items}
    goal_item = next((item for item in items if item["kind"] == "research_question"), None)

    mapping: dict[str, list[str]] = {}
    for intent in intents:
        intent_id = str(intent.get("intent_id") or intent.get("id") or "")
        if not intent_id:
            continue
        targets: set[str] = set()
        for milestone_id in (intent.get("related_milestone_ids") or []):
            if str(milestone_id) in by_yaml_id:
                targets.add(by_yaml_id[str(milestone_id)])
        for ref in (intent.get("source_refs") or []):
            text = str(ref or "")
            if text.startswith("milestone:"):
                title = text[len("milestone:"):].strip()
                if title in by_title:
                    targets.add(by_title[title])
            elif text.startswith("next_action:"):
                title = text[len("next_action:"):].strip()
                if title in by_title:
                    targets.add(by_title[title])
            elif text.startswith("research_question:"):
                if goal_item is not None:
                    targets.add(goal_item["work_item_id"])
        for work_item_id in targets:
            mapping.setdefault(work_item_id, []).append(intent_id)
    return mapping


def materialize_links(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
) -> dict[str, dict[str, Any]]:
    """Compute per-work-item links from runs, ledger claims, papers and branch.

    Returns ``{work_item_id: {linked_run_ids, linked_paper_keys,
    evidence_refs, linked_branch}}`` — all fields stay contract-shaped
    (string lists).  Radar-run links flow through the intent map; query-run
    links come from run metadata (work_item_id).
    """
    items = work_item_projection(project)
    links: dict[str, dict[str, Any]] = {
        item["work_item_id"]: {
            "linked_run_ids": [],
            "linked_paper_keys": [],
            "evidence_refs": [],
            "linked_branch": "",
        }
        for item in items
    }

    # Intent map (radar runs + paper matches route through intents).
    intent_map = intent_work_item_map(intelligence, project)
    linked_intents: dict[str, set[str]] = {
        work_item_id: set(intent_ids) for work_item_id, intent_ids in intent_map.items()
    }

    # Query runs: RunStore metadata carries project_id + work_item_id.
    query_run_ids_by_item: dict[str, list[str]] = {}
    try:
        runs = RunStore(intelligence.db).list(limit=100)
    except Exception:
        runs = []
    for run in runs:
        metadata = run.get("metadata") or {}
        if str(metadata.get("project_id") or "") != project.id:
            continue
        work_item_id = str(metadata.get("work_item_id") or "")
        if work_item_id and work_item_id in links:
            query_run_ids_by_item.setdefault(work_item_id, []).append(
                str(run.get("run_id") or "")
            )

    # Radar runs: one latest search run per project, routed via intent map.
    radar_run_ids: list[str] = []
    try:
        latest = SearchRunStore(intelligence.db).latest(project.id)
    except Exception:
        latest = None
    if latest and latest.get("run_id"):
        radar_run_ids.append(str(latest["run_id"]))

    ledger = EvidenceLedgerRepository(intelligence.db)
    for work_item_id, state in links.items():
        runs_seen: set[str] = set()
        for run_id in query_run_ids_by_item.get(work_item_id, []):
            if not run_id or run_id in runs_seen:
                continue
            runs_seen.add(run_id)
            state["linked_run_ids"].append(run_id)
            # Claims from the Evidence Ledger become evidence refs with
            # source version (claim id + verdict + confidence).
            try:
                ledger_run = ledger.run_ledger(run_id)
            except Exception:
                ledger_run = {"claims": []}
            for claim in (ledger_run or {}).get("claims") or []:
                verification = claim.get("verification") or claim.get("verification_json") or {}
                verdict = str(verification.get("verdict") or "uncertain")
                confidence = verification.get("confidence")
                state["evidence_refs"].append(
                    f"claim:{claim.get('claim_id')}:{verdict}:{confidence}"
                )
        if radar_run_ids and work_item_id in linked_intents:
            for run_id in radar_run_ids:
                if run_id not in runs_seen:
                    state["linked_run_ids"].append(run_id)

        # Paper links: saved/shortlisted project papers matched to intents
        # or to YAML milestone ids directly.
        paper_keys: list[str] = []
        try:
            papers = ProjectPaperStore(intelligence.db).list(project.id)
        except Exception:
            papers = []
        intent_ids = linked_intents.get(work_item_id, set())
        # YAML milestone id -> the exact work item that carries it.
        yaml_id_to_item: dict[str, str] = {}
        for index, milestone in enumerate(project.plan.milestones):
            if milestone.id:
                yaml_id_to_item[milestone.id] = f"{project.id}:wi:ms-{index}"
        item_milestone_ids = {
            milestone_id for milestone_id, item_id in yaml_id_to_item.items()
            if item_id == work_item_id
        }
        for paper in papers or []:
            if str(paper.get("status") or "") not in {"saved", "shortlisted"}:
                continue
            matched_intents = set(paper.get("matched_intent_ids") or [])
            matched_milestones = set(paper.get("matched_milestone_ids") or [])
            if intent_ids & matched_intents:
                paper_keys.append(str(paper.get("paper_key") or ""))
            elif matched_milestones & item_milestone_ids:
                paper_keys.append(str(paper.get("paper_key") or ""))
        state["linked_paper_keys"] = sorted({key for key in paper_keys if key})

        # Branch link: persisted user confirmation lives in the store row;
        # materialization only carries it forward.
        existing = intelligence.work_items.get(work_item_id)
        if existing is not None and existing.linked_branch:
            state["linked_branch"] = existing.linked_branch

    return links


def derive_observed(inferred_from: dict[str, Any], declared_status: str) -> str:
    """Bounded observed-status rules (plan §9.3).

    Evidence verdicts (contradicts/insufficient) are negative; any evidence
    at all upgrades no_evidence, but completed still requires a supporting
    claim to be called verified.
    """
    evidence = inferred_from.get("evidence_refs") or []
    if any(":contradicts:" in ref or ":insufficient:" in ref for ref in evidence):
        return ObservedStatus.FAILED.value
    supports = [ref for ref in evidence if ":supports:" in ref]
    if declared_status == "completed" and supports:
        return ObservedStatus.VERIFIED.value
    if supports or (inferred_from.get("linked_run_ids") or []):
        return ObservedStatus.ACTIVE.value
    return ObservedStatus.NO_EVIDENCE.value


def derive_inferred(declared_status: str, observed_status: str) -> str:
    if declared_status == "blocked":
        return "blocked"
    if observed_status in {"failed"}:
        return "needs_review"
    if declared_status == "completed":
        return "completed" if observed_status == "verified" else "needs_review"
    return declared_status


def persist_links(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
) -> list[dict[str, Any]]:
    """Merge projection + links into the work-items store; returns merged items.

    The store row keeps the link/evidence fields (they have no YAML home);
    the projection remains authoritative for declared fields.
    """
    links = materialize_links(intelligence, project)
    merged: list[dict[str, Any]] = []
    for item in work_item_projection(project):
        work_item_id = item["work_item_id"]
        link = links.get(work_item_id, {
            "linked_run_ids": [], "linked_paper_keys": [],
            "evidence_refs": [], "linked_branch": "",
        })
        observed = derive_observed(link, item["declared_status"])
        inferred = derive_inferred(item["declared_status"], observed)
        final = dict(item)
        final["linked_run_ids"] = list(link["linked_run_ids"])
        final["linked_paper_keys"] = list(link["linked_paper_keys"])
        final["evidence_refs"] = list(link["evidence_refs"])
        final["linked_branch"] = str(link["linked_branch"] or "")
        final["observed_status"] = observed
        final["inferred_status"] = inferred
        intelligence.work_items.upsert(ResearchWorkItem(**final))
        merged.append(final)
    return merged
