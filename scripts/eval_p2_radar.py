"""Score Paper Radar runs against the P2 labeled set.

Usage:
    python scripts/eval_p2_radar.py \
        --labels evaluation/p2_radar/labels.jsonl \
        --run <radar_result.json>  # RadarRunResult.model_dump() or radar run JSON \
        --output reports/evaluation/p2_radar/result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.evaluation_p2 import (  # noqa: E402
    aggregate_p2_results,
    evaluate_p2_run,
    load_p2_labels,
    merge_repeated_evaluations,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score P2 Paper Radar runs against labels")
    parser.add_argument("--labels", default=str(PROJECT_ROOT / "evaluation" / "p2_radar" / "labels.jsonl"))
    parser.add_argument("--run", action="append", default=[], metavar="LABEL=RUN_JSON")
    parser.add_argument("--merge", action="store_true",
                        help="aggregate repeated evaluations (median/min/max) from --run result JSONs")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    labels = load_p2_labels(args.labels)
    results = []
    for value in args.run:
        label, separator, path = value.partition("=")
        if not separator or not label:
            parser.error("--run must use LABEL=RUN_JSON")
        run = json.loads(Path(path).read_text(encoding="utf-8"))
        results.append({**evaluate_p2_run(run, labels), "run_label": label})

    if args.merge:
        if not args.run:
            parser.error("--merge requires at least one --run")
        merged_runs = []
        for value in args.run:
            _, separator, path = value.partition("=")
            if not separator:
                parser.error("--run must use LABEL=RUN_JSON")
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            merged_runs.extend(payload.get("results") or [])
        merged = merge_repeated_evaluations(merged_runs)
        output = json.dumps(merged, ensure_ascii=False, indent=2)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"Wrote: {output_path}")
        else:
            print(output)
        return 0

    if not results:
        parser.error("at least one --run is required")

    payload = {
        "schema_version": "conflux-p2-radar-eval-v1",
        "label_set": str(args.labels),
        "results": results,
        "aggregate": aggregate_p2_results(results),
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Wrote: {output_path}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
