"""End-to-end gate statistics.

Collects FactCheck, Quality Gate, and Delivery Gate pass/fail rates
from a directory of run summaries (V2 or P1/P1.5).

Usage:
  python scripts/eval_gates.py --summaries-dir reports/v2-hk-verify/ [--pipeline v2]
  python scripts/eval_gates.py --summaries-dir reports/workbench/   [--pipeline p15]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def collect_summaries(directory: Path) -> list[dict[str, Any]]:
    """Load all .summary.json files from a directory (non-recursive)."""
    summaries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.summary.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_source_file"] = path.name
            summaries.append(data)
        except Exception:
            continue
    return summaries


def compute_gate_stats(summaries: list[dict[str, Any]], pipeline: str) -> dict[str, Any]:
    """Compute pass/fail distribution across all gates."""
    total = len(summaries)
    if total == 0:
        return {"total_runs": 0}

    # ── Confidence / FactCheck status ──
    confidence_counts: Counter[str] = Counter()
    factcheck_statuses: Counter[str] = Counter()
    run_statuses: Counter[str] = Counter()

    # ── Quality metrics ──
    quality_overalls: list[float] = []
    quality_passed = 0

    # ── Delivery status ──
    delivery_counts: Counter[str] = Counter()

    for s in summaries:
        # Confidence
        conf = str(s.get("confidence") or "").strip()
        if conf:
            confidence_counts[conf] += 1
        else:
            confidence_counts["unavailable"] += 1

        # FactCheck
        fc = str(s.get("factcheck_status") or "").strip()
        if fc:
            factcheck_statuses[fc] += 1
        else:
            factcheck_statuses["unavailable"] += 1

        # Run status
        rs = str(s.get("run_status") or "").strip()
        run_statuses[rs] += 1 if rs else 0

        # Quality
        quality = s.get("quality") or {}
        if isinstance(quality, dict):
            overall = quality.get("overall")
            if isinstance(overall, (int, float)):
                quality_overalls.append(float(overall))
            if quality.get("passed"):
                quality_passed += 1

        # Delivery
        ds = str(s.get("delivery_status") or "").strip()
        if ds:
            delivery_counts[ds] += 1
        else:
            # V2 uses confidence as proxy for delivery readiness
            if conf in ("high", "medium"):
                delivery_counts["confidence_based"] += 1
            else:
                delivery_counts["unclassified"] += 1

    stats: dict[str, Any] = {
        "total_runs": total,
        "pipeline": pipeline,
    }

    # Confidence distribution
    stats["confidence_distribution"] = dict(confidence_counts)
    confidence_high = confidence_counts.get("high", 0)
    confidence_medium = confidence_counts.get("medium", 0)
    stats["confidence_high_or_medium_rate"] = round(
        (confidence_high + confidence_medium) / total, 3
    )

    # FactCheck status distribution
    stats["factcheck_distribution"] = dict(factcheck_statuses)
    stats["factcheck_pass_rate"] = round(
        factcheck_statuses.get("passed", 0) / max(1, total), 3
    )

    # Run completion
    completed = run_statuses.get("completed", 0)
    partial = run_statuses.get("partial", 0)
    stats["run_completion_rate"] = round((completed + partial) / total, 3)
    stats["run_status_distribution"] = dict(run_statuses)

    # Quality Gate
    stats["quality_mean_overall"] = round(statistics.mean(quality_overalls), 2) if quality_overalls else 0
    stats["quality_median_overall"] = round(statistics.median(quality_overalls), 2) if quality_overalls else 0
    stats["quality_pass_rate"] = round(quality_passed / total, 3)

    # Delivery Gate
    stats["delivery_distribution"] = dict(delivery_counts)
    deliverable = delivery_counts.get("deliverable", 0)
    limited = delivery_counts.get("limited", 0)
    confidence_based = delivery_counts.get("confidence_based", 0)
    stats["delivery_ready_rate"] = round(
        (deliverable + limited + confidence_based) / total, 3
    )

    # Evidence metrics (V2)
    evidence_coverages: list[float] = []
    sections_with_ext: list[int] = []
    citation_ref_totals: list[int] = []
    for s in summaries:
        audit = s.get("audit") or {}
        if isinstance(audit, dict):
            ec = audit.get("external_evidence_coverage")
            if isinstance(ec, (int, float)):
                evidence_coverages.append(float(ec))
            swe = audit.get("sections_with_external_evidence")
            if isinstance(swe, int):
                sections_with_ext.append(swe)
            tcr = audit.get("total_citation_refs")
            if isinstance(tcr, int):
                citation_ref_totals.append(tcr)

    if evidence_coverages:
        stats["mean_external_evidence_coverage"] = round(statistics.mean(evidence_coverages), 3)
    if sections_with_ext:
        stats["mean_sections_with_ext"] = round(statistics.mean(sections_with_ext), 1)
    if citation_ref_totals:
        stats["mean_total_citation_refs"] = round(statistics.mean(citation_ref_totals), 1)

    return stats


def write_gate_report(stats: dict[str, Any], out_path: Path) -> Path:
    lines = [
        "# End-to-End Gate Statistics",
        "",
        f"**Pipeline**: {stats.get('pipeline', 'N/A')}  |  "
        f"**Total runs**: {stats.get('total_runs', 0)}",
        "",
        "## Gate Pass Rates",
        "",
        "| Gate | Metric | Value |",
        "|---|---|---|",
        f"| Run Completion | completed + partial / total | {stats.get('run_completion_rate', 0):.1%} |",
        f"| Confidence | high + medium / total | {stats.get('confidence_high_or_medium_rate', 0):.1%} |",
        f"| FactCheck | passed / total | {stats.get('factcheck_pass_rate', 0):.1%} |",
        f"| Quality | passed / total | {stats.get('quality_pass_rate', 0):.1%} |",
        f"| Delivery | ready / total | {stats.get('delivery_ready_rate', 0):.1%} |",
        "",
        "## Confidence Distribution",
        "",
        "| Level | Count |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(stats.get("confidence_distribution", {}).items())],
        "",
        "## FactCheck Status Distribution",
        "",
        "| Status | Count |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(stats.get("factcheck_distribution", {}).items())],
        "",
        "## Run Status Distribution",
        "",
        "| Status | Count |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(stats.get("run_status_distribution", {}).items())],
        "",
        "## Delivery Distribution",
        "",
        "| Status | Count |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(stats.get("delivery_distribution", {}).items())],
        "",
        "## Evidence Quality (V2)",
        "",
    ]

    if stats.get("mean_external_evidence_coverage"):
        lines.extend([
            f"- Mean external evidence coverage: {stats['mean_external_evidence_coverage']:.3f}",
            f"- Mean sections with ext evidence: {stats.get('mean_sections_with_ext', 0):.1f}",
            f"- Mean total citation refs: {stats.get('mean_total_citation_refs', 0):.1f}",
        ])
    else:
        lines.append("- No V2 audit data available")

    lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end gate statistics.")
    parser.add_argument("--summaries-dir", required=True, help="Directory of .summary.json files")
    parser.add_argument("--pipeline", default="v2", choices=("v2", "p1", "p15"), help="Pipeline type")
    parser.add_argument("--out-dir", default="reports/eval/gates")
    args = parser.parse_args()

    summaries_dir = Path(args.summaries_dir)
    if not summaries_dir.is_dir():
        print(f"Error: not a directory: {summaries_dir}")
        return 1

    summaries = collect_summaries(summaries_dir)
    print(f"Loaded {len(summaries)} summaries from {summaries_dir}")

    stats = compute_gate_stats(summaries, args.pipeline)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "gate_stats.json"
    md_path = out_dir / "gate_stats.md"

    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    write_gate_report(stats, md_path)

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")

    # Quick summary
    print(f"\nCompletion: {stats.get('run_completion_rate', 0):.1%} | "
          f"Confidence (high+med): {stats.get('confidence_high_or_medium_rate', 0):.1%} | "
          f"FactCheck pass: {stats.get('factcheck_pass_rate', 0):.1%} | "
          f"Quality pass: {stats.get('quality_pass_rate', 0):.1%} | "
          f"Delivery ready: {stats.get('delivery_ready_rate', 0):.1%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
