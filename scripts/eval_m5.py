"""Build the M5 evaluation report from a frozen manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conflux.evaluation_m5 import evaluate_manifest, render_markdown  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the M5 review and ablation report")
    parser.add_argument("--manifest", default="evaluation/m5/manifest.json")
    parser.add_argument("--output-dir", default="reports/evaluation/m5")
    args = parser.parse_args(argv)
    manifest_path = (ROOT / args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = evaluate_manifest(manifest, root=ROOT)
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "m5_evaluation.json"
    md_path = output_dir / "m5_evaluation.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"M5 JSON: {json_path}")
    print(f"M5 Markdown: {md_path}")
    return 0 if all(bool(value) for value in result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
