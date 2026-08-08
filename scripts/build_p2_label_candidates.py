"""Build P2 labeled-set candidates from a real multi-Track radar retrieval.

Runs the real arXiv source for every Track QuerySpec in the profile,
exports candidate details for labeling, and runs the radar pipeline to
produce links/stats for evaluation.

Usage:
    python scripts/build_p2_label_candidates.py \
        --profile profiles/example_gis_agent.yaml \
        --max-results 15 \
        --out-dir reports/evaluation/p2_radar/label_run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build P2 labeled-set candidates")
    parser.add_argument("--profile", default="profiles/example_gis_agent.yaml")
    parser.add_argument("--max-results", type=int, default=15)
    parser.add_argument("--delay", type=float, default=8.0, help="seconds between arXiv queries (rate-limit safety)")
    parser.add_argument("--llm-review", action="store_true", help="enable batch LLM semantic review (costs LLM calls)")
    parser.add_argument("--out-dir", default="reports/evaluation/p2_radar/label_run")
    args = parser.parse_args()

    from conflux.core.p2_contracts import PaperSource, ProjectResearchConfig
    from conflux.paper_ingestion.arxiv_source import search_arxiv
    from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    profile = load_profile(args.profile, validate=False)
    config = ProjectResearchConfig(
        profile=args.profile,
        sources=[PaperSource.ARXIV],
        max_candidates=100,
        deep_read_limit=0,
    )
    queries = resolve_query_specs_from_profile(profile, config=config)
    print(f"[info] {len(queries)} QuerySpecs from {len(profile.get_tracks())} tracks")

    candidates: list[dict] = []
    for index, spec in enumerate(queries):
        try:
            papers = search_arxiv(
                spec.query,
                max_results=args.max_results,
                categories=list(getattr(spec, "categories", None) or []),
            )
        except Exception as exc:
            print(f"[warn] query {spec.id} failed: {exc}")
            continue
        for rank, paper in enumerate(papers, start=1):
            candidates.append({
                "query_id": spec.id,
                "track_id": spec.track_id,
                "query_text": spec.query,
                "paper_id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract or "",
                "source": paper.source,
                "doi": paper.doi or "",
                "retrieval_rank": rank,
            })
        print(f"[info] {spec.track_id} {spec.id}: {len(papers)} candidates")
        if index < len(queries) - 1:
            time.sleep(args.delay)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = out_dir / "candidates.jsonl"
    with open(candidate_path, "w", encoding="utf-8") as fh:
        for row in candidates:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote: {candidate_path} ({len(candidates)} candidates)")

    # Run the radar pipeline (no LLM deep analysis) for links/stats.
    proj = ProjectDefinition(id="radar-label-run", name="Radar Label Run", path=str(PROJECT_ROOT))
    proj.plan.overall_goal = "验证知识图谱增强 GIS Agent 工作流的有效性与可复现性"
    proj.research = {
        "profile": args.profile,
        "sources": ["arxiv"],
        "max_candidates": 100,
        "deep_read_limit": 0,
    }
    started = time.time()
    review_model = None
    if args.llm_review:
        from conflux.model_factory import create_chat_model
        review_model = create_chat_model("balanced")
        print("[info] batch LLM semantic review enabled (balanced)")
    result = run_paper_radar(
        proj,
        profile,
        out_dir=str(out_dir / "radar"),
        llm_review=args.llm_review,
        review_model=review_model,
    )
    elapsed = time.time() - started
    run_payload = {
        "run_id": result.stats.run_id,
        "elapsed_seconds": elapsed,
        "links": [link.model_dump() for link in result.links],
        "suggestions": [s.model_dump() for s in result.suggestions],
        "stats": result.stats.model_dump(),
        "queries": [q.model_dump() for q in result.queries],
    }
    run_path = out_dir / "radar_run.json"
    run_path.write_text(json.dumps(run_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote: {run_path} (links={len(result.links)}, elapsed={elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
