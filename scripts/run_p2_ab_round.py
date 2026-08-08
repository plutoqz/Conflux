"""Run one controlled P2 Paper Radar A/B round from a frozen candidate pool.

Usage:
    python scripts/run_p2_ab_round.py \
        --export-candidates evaluation/p2_radar/candidates_ab_20260808.jsonl

    python scripts/run_p2_ab_round.py \
        --candidates evaluation/p2_radar/candidates_ab_20260808.jsonl \
        --label old-1 --temperature 0.25 --no-layered \
        --out-dir reports/evaluation/p2_radar/ab_old_1
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


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def export_candidates(out_path: Path) -> int:
    from conflux.core.p2_contracts import PaperSource, ProjectResearchConfig
    from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
    from conflux.paper_radar.radar import _execute_queries
    from conflux.research_profile import load_profile

    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    config = ProjectResearchConfig(
        profile="profiles/example_gis_agent.yaml",
        sources=[PaperSource.ARXIV],
        max_candidates=100,
        deep_read_limit=0,
    )
    queries = resolve_query_specs_from_profile(profile, config=config)
    papers, failed = _execute_queries(queries)
    rows = [paper.to_dict() for paper in papers]
    _write_jsonl(out_path, rows)
    print(f"Wrote: {out_path} ({len(rows)} candidates, failed={failed})")
    return 0


def run_round(args: argparse.Namespace) -> int:
    from conflux.model_factory import create_chat_model
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.paper_radar import radar
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    candidates_path = Path(args.candidates)
    papers = [
        PaperRecord.from_dict(json.loads(line))
        for line in candidates_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def frozen_execute(queries, stats=None):
        return list(papers), []

    radar._execute_queries = frozen_execute

    proj = ProjectDefinition(id="radar-label-run", name="Radar Label Run", path=str(PROJECT_ROOT))
    proj.plan.overall_goal = "验证知识图谱增强 GIS Agent 工作流的有效性与可复现性"
    proj.research = {
        "profile": "profiles/example_gis_agent.yaml",
        "sources": ["arxiv"],
        "max_candidates": 100,
        "deep_read_limit": 0,
    }
    profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
    review_model = create_chat_model("balanced", temperature=args.temperature)

    started = time.time()
    result = run_paper_radar(
        proj,
        profile,
        out_dir=str(out_dir / "radar"),
        llm_review=True,
        review_model=review_model,
        layered_review=not args.no_layered,
        review_mode=args.review_mode,
        review_few_shot=args.few_shot,
        review_chunk_size=args.review_chunk_size,
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
    run_path.write_text(
        json.dumps(run_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    config_payload = {
        "label": args.label,
        "temperature": args.temperature,
        "layered": not args.no_layered,
        "review_mode": args.review_mode,
        "few_shot": args.few_shot,
        "review_chunk_size": args.review_chunk_size,
        "candidates": str(candidates_path),
        "semantic_review_calls": result.stats.semantic_review_calls,
        "semantic_review_tokens": result.stats.semantic_review_tokens,
        "semantic_review_failed": result.stats.semantic_review_failed,
        "elapsed_seconds": round(elapsed, 3),
    }
    (out_dir / "config.json").write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Wrote: {run_path} "
        f"(label={args.label}, layered={not args.no_layered}, "
        f"temp={args.temperature}, tokens={result.stats.semantic_review_tokens})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one controlled P2 A/B round")
    parser.add_argument("--candidates", default="", help="frozen PaperRecord JSONL snapshot")
    parser.add_argument("--export-candidates", default="", help="export exact query candidates and exit")
    parser.add_argument("--label", default="round")
    parser.add_argument("--temperature", type=float, default=0.25)
    parser.add_argument("--no-layered", action="store_true")
    parser.add_argument("--review-mode", choices=["pointwise", "listwise"], default="pointwise")
    parser.add_argument("--review-chunk-size", type=int, default=8)
    parser.add_argument("--few-shot", action="store_true")
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args(argv)

    if args.export_candidates:
        return export_candidates(Path(args.export_candidates))
    if not args.candidates or not args.out_dir:
        parser.error("--candidates and --out-dir are required for a run round")
    return run_round(args)


if __name__ == "__main__":
    raise SystemExit(main())
