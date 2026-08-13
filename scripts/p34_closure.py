"""P3.4 closure runner — 缺口 -> 查询(replay) -> 证据 -> 计划复核 for ONE project.

Generic over any registered project with a plan (no project-specific
hardcoding — the target work item is picked by deterministic rules from the
YAML plan).  Uses the fixed replay bundle so the query runs offline and
deterministically; the Evidence Ledger is persisted to the real research
database, then the P3 refresh materializes the links into the snapshot.

Usage:
    python scripts/p34_closure.py <project_id> [--out reports/evaluation/p3]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux import config  # noqa: E402
from conflux.adapters.sqlite_store import RunStore, SQLiteDatabase  # noqa: E402
from conflux.core.runtime_home import database_path  # noqa: E402
from conflux.project_registry import ProjectRegistry  # noqa: E402
from conflux.projects import (  # noqa: E402
    ProjectIntelligence,
    SnapshotTrigger,
    build_snapshot,
    collect_all_events,
    ingest_events,
    persist_links,
    seed_reviews,
)
from conflux.projects.discovery_service import scan_project_documents  # noqa: E402
from conflux.projects.rag_coverage import compute_coverage  # noqa: E402


def _replay_bundle(query: str, run_id: str) -> dict:
    """Fixed deterministic replay bundle; query text is project-specific."""
    evidence_id = f"{run_id}:ev-0001"
    claim_id = f"{run_id}:claim:sq-1:01"
    return {
        "schema_version": "conflux-v2-replay-v1",
        "run_id": run_id,
        "query": query,
        "depth": "standard",
        "prompt_version": "research-prompts-v3",
        "model_config_version": "research-model-profile-v1",
        "models": {
            "planner": {"responses": [
                {"content": '{"core_question":"' + query + '","sub_questions":[{"question":"replay verification","search_queries":["replay verification"],"search_queries_en":[]}]}'},
                {"content": '{"judgments":[{"subquestion_id":"sq-1","verdict":"covered","confidence":1.0}],"action_proposals":[]}'},
            ]},
            "analyst": {"responses": [{"content": '{"summary":"independent replay analysis"}'}]},
            "synthesizer": {"responses": [
                {"content": '{"claims":[{"text":"Replay uses fixed provider responses.","claim_type":"direct_fact","importance":"high",'
                           f'"evidence_ids":["{evidence_id}"],"derivation_type":"direct_evidence","citation_refs":["[1]"]}}]}}'},
                {"content": '{"direct_claim_ids":["' + claim_id + '"],"cross_synthesis_claim_ids":["' + claim_id + '"]}'},
            ]},
            "verifier": {"responses": [
                {"content": '{"checks":[{"claim_id":"' + claim_id + '","verdict":"supports","confidence":1.0,'
                           f'"evidence_ids":["{evidence_id}"]}}]}}'},
            ]},
        },
        "retrieval": {
            "RAG": {"by_query": {"replay verification": {
                "status": "success",
                "content": "Replay uses fixed provider responses.",
                "claims": [{
                    "claim": "Replay uses fixed provider responses so every pipeline step consumes only recorded payloads without calling live providers.",
                    "verbatim_quote": "Replay uses fixed provider responses so every pipeline step consumes only recorded payloads without calling live providers.",
                    "source_identity": "replay-rag",
                    "content_hash": "replay-rag-hash",
                    "evidence_class": "authoritative_document",
                    "relevance": 0.9,
                }],
            }}},
            "Web": {"by_query": {"replay verification": {"status": "no_evidence", "content": ""}}},
        },
    }


def _pick_target_work_item(project) -> tuple[dict, str]:
    """Deterministic target selection: in_progress milestone -> action ->
    planned milestone -> goal.  Returns (item, reason)."""
    from conflux.projects.projections import work_item_projection

    items = work_item_projection(project)
    if not items:
        return {}, "计划为空（无目标/里程碑/行动），无法建立闭环载体。"
    for item in items:
        if item["kind"] == "milestone" and item["declared_status"] == "in_progress":
            return item, "选择进行中的里程碑"
    for item in items:
        if item["kind"] == "action":
            return item, "选择后续行动"
    for item in items:
        if item["kind"] == "milestone":
            return item, "选择首个里程碑（无进行中项）"
    return items[0], "选择研究问题"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p3"))
    args = parser.parse_args()

    registry = ProjectRegistry(str(PROJECT_ROOT / "projects"), base_dir=PROJECT_ROOT)
    project = registry.get(args.project_id)
    if project is None:
        print(f"[closure] 项目未找到：{args.project_id}")
        return 1

    item, reason = _pick_target_work_item(project)
    if not item:
        print(f"[closure] {args.project_id}: {reason}")
        return 2
    work_item_id = item["work_item_id"]
    query_text = f"围绕研究重点「{item['title']}」，找出证据缺口和验证方式"
    print(f"[closure] {args.project_id}: {reason} -> {item['kind']}「{item['title']}」({work_item_id})")

    run_id = f"p34-{args.project_id}-{int(time.time()) % 100000}"
    bundle = _replay_bundle(query_text, run_id)
    out_dir = Path(args.out) / "closure" / args.project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / f"{run_id}.replay.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    # 1) Register the run in the durable store with its work-item context.
    db_path = database_path()
    db = SQLiteDatabase(db_path).connect()
    db.bootstrap_schema()
    try:
        RunStore(db).create_run(
            run_id=run_id,
            status="running",
            metadata={"project_id": project.id, "work_item_id": work_item_id,
                      "query": query_text, "source": "p34_closure"},
        )
    finally:
        db.close()

    # 2) Run the real V2 graph offline (replay) and persist the ledger.
    from conflux.__main__ import query_command

    query_command(
        query_text,
        output_dir=str(out_dir),
        trace_dir=str(out_dir),
        replay=str(bundle_path),
        depth="standard",
        ledger_db_path=str(db_path),
    )

    # 3) Close the run with the recorded budget.
    summary_path = out_dir / f"{run_id}.summary.json"
    budget = {}
    if summary_path.exists():
        budget = json.loads(summary_path.read_text(encoding="utf-8")).get("budget_consumed") or {}
    db = SQLiteDatabase(db_path).connect()
    db.bootstrap_schema()
    try:
        RunStore(db).update_metadata(
            run_id,
            {"status": "completed", "budget_consumed": budget},
            status="completed",
        )
    finally:
        db.close()

    # 4) P3 refresh: events + links + reviews + snapshot (with RAG coverage).
    intelligence = ProjectIntelligence(SQLiteDatabase(db_path).connect())
    intelligence.ensure_schema()
    try:
        events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
        added = ingest_events(intelligence, events)
        scan_project_documents(intelligence, project)
        rag = compute_coverage(intelligence, project)
        seeded = seed_reviews(intelligence, project, rag=rag)
        snapshot = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL, rag=rag)
        items = persist_links(intelligence, project)
    finally:
        intelligence.db.close()

    # 5) Collect closure evidence.
    target = next(candidate for candidate in items if candidate["work_item_id"] == work_item_id)
    pending_reviews = []
    intelligence = ProjectIntelligence(SQLiteDatabase(db_path).connect())
    intelligence.ensure_schema()
    try:
        for review in intelligence.reviews.list(project.id, status="pending"):
            if work_item_id in (review.impact_refs or []) or run_id in (review.impact_refs or []):
                pending_reviews.append({
                    "review_id": review.review_id,
                    "kind": review.kind.value,
                    "summary": review.summary,
                    "proposed_action": review.proposed_action,
                })
    finally:
        intelligence.db.close()

    report = {
        "project_id": project.id,
        "work_item_id": work_item_id,
        "work_item": {
            "kind": item["kind"],
            "title": item["title"],
            "declared_status": target["declared_status"],
            "observed_status": target["observed_status"],
            "inferred_status": target["inferred_status"],
        },
        "gap": {"acceptance_criteria": item.get("acceptance_criteria") or [],
                "selection_reason": reason},
        "query": {"run_id": run_id, "replay": str(bundle_path), "tokens": budget},
        "links": {
            "linked_run_ids": target.get("linked_run_ids") or [],
            "linked_paper_keys": target.get("linked_paper_keys") or [],
            "evidence_refs": target.get("evidence_refs") or [],
        },
        "reviews_pending": pending_reviews,
        "snapshot_revision": snapshot.revision,
        "events_added": added,
        "reviews_added": len(seeded),
    }
    report_path = out_dir / f"closure_{project.id}_{int(time.time()) % 100000}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[closure] 完成：快照 v{snapshot.revision}，运行链接 {len(target.get('linked_run_ids') or [])} 项，"
          f"证据 {len(target.get('evidence_refs') or [])} 条，待处理复核 {len(pending_reviews)} 项")
    print(f"[closure] 报告：{report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
