"""Score V2 run summaries against the §8.10 Gold assets.

Example:
    python scripts/eval_v2_gold.py \
      --run evidenceledger-limitations-smoke=reports/v2_real_smoke2/3b4390afe7b3.summary.json \
      --output reports/evaluation/v2_gold/initial_evaluation.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.evaluation_gold import load_gold_bundle, score_runs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score V2 summaries against §8.10 Gold")
    parser.add_argument("--gold-dir", default=str(PROJECT_ROOT / "evaluation" / "v2_gold"))
    parser.add_argument("--run", action="append", default=[], metavar="CASE_ID=SUMMARY_JSON")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    run_summaries: dict[str, dict] = {}
    for value in args.run:
        case_id, separator, path = value.partition("=")
        if not separator or not case_id:
            parser.error("--run must use CASE_ID=SUMMARY_JSON")
        run_summaries[case_id] = json.loads(Path(path).read_text(encoding="utf-8"))

    if not run_summaries:
        parser.error("at least one --run is required")

    result = score_runs(run_summaries, load_gold_bundle(args.gold_dir))
    output = json.dumps(result, ensure_ascii=False, indent=2)
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
