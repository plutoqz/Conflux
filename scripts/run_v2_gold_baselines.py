"""Run the B2/B3/B4 fixed-replay baselines and score each against Gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.__main__ import query_command  # noqa: E402
from conflux.evaluation_gold import load_gold_bundle, score_runs  # noqa: E402
from conflux.replay import load_replay_bundle  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run B2/B3/B4 on one fixed replay bundle and score each condition."
    )
    parser.add_argument(
        "--replay",
        default=str(
            PROJECT_ROOT
            / "evaluation"
            / "v2_gold"
            / "replay"
            / "evidenceledger-limitations-baseline.json"
        ),
    )
    parser.add_argument("--case-id", default="evidenceledger-limitations-replay")
    parser.add_argument("--gold-dir", default=str(PROJECT_ROOT / "evaluation" / "v2_gold"))
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "reports" / "evaluation" / "v2_gold" / "baselines"),
    )
    parser.add_argument("--variants", nargs="+", choices=["B2", "B3", "B4"], default=["B2", "B3", "B4"])
    parser.add_argument("--depth", default="deep")
    args = parser.parse_args(argv)

    replay_path = Path(args.replay)
    bundle = load_replay_bundle(replay_path)
    query = str(bundle.get("query") or "").strip()
    run_id = str(bundle.get("run_id") or "").strip()
    if not query or not run_id:
        parser.error("replay bundle must provide query and run_id")

    gold = load_gold_bundle(args.gold_dir)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in args.variants:
        variant_dir = output_root / variant
        query_command(
            query,
            output_dir=str(variant_dir),
            trace_dir=str(variant_dir),
            replay=str(replay_path),
            depth=args.depth,
            baseline_variant=variant,
        )
        summary_path = variant_dir / f"{run_id}.summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        score = score_runs({args.case_id: summary}, gold)
        score_path = variant_dir / "evaluation.json"
        score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append({
            "variant": variant,
            "summary": str(summary_path),
            "evaluation": str(score_path),
            "baseline_policy": summary.get("baseline_policy") or {},
            "aggregate": score["aggregate"],
        })

    comparison = {
        "schema_version": "conflux-v2-baseline-results-v1",
        "case_id": args.case_id,
        "fixture_type": str(bundle.get("fixture_type") or "fixed_replay"),
        "fixture_note": str(bundle.get("fixture_note") or ""),
        "replay_bundle": str(replay_path),
        "conditions": results,
        "interpretation": (
            "B2/B3/B4 are replay-equivalent workflow comparisons. They do not replace "
            "live-provider quality, latency, token, or cost validation."
        ),
    }
    comparison_path = output_root / "baseline_comparison.json"
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {comparison_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
