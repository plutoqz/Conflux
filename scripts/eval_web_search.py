"""Web search quality evaluation.

Runs a set of time-sensitive queries through Conflux's web search pipeline,
collecting hit rate, fetch success rate, effective evidence rate, and
provider distribution statistics.

Usage:
  python scripts/eval_web_search.py [--k 18] [--out-dir reports/eval/web]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def load_queries(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"web eval queries must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def run_one_query(
    item: dict[str, Any],
    web_tool,
    deadline_at: float,
) -> dict[str, Any]:
    """Execute one web search and collect structured metrics.

    注意：fetch 层超时由 web 工具内部控制（config `web_search.fetch_timeout_seconds`
    与 run deadline），本函数不重复传入 fetch_timeout，避免死参数误导。
    """
    query = str(item["query"])
    t0 = time.time()

    try:
        if time.time() > deadline_at:
            return {"query": query, "status": "skipped_deadline", "error": "global deadline exceeded"}

        raw = web_tool.invoke({"query": query}) if hasattr(web_tool, "invoke") else web_tool(query)
        elapsed = time.time() - t0

        # Parse results
        parsed = _parse_web_result(str(raw) if not isinstance(raw, str) else raw)

        return {
            "id": item.get("id", ""),
            "query": query,
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            **parsed,
        }
    except Exception as exc:
        elapsed = time.time() - t0
        return {
            "id": item.get("id", ""),
            "query": query,
            "status": "failed",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc)[:200],
        }


def _parse_web_result(raw: str) -> dict[str, Any]:
    """Parse web search output text into structured metrics.

    Conflux web search returns formatted text with sections:
    - 检索统计: hit count, fetch count
    - 有效证据: evidence items
    - Each evidence item starts with [Fetched N] or [RunScoped N]
    """
    import re

    lines = raw.split("\n")

    hit_count = 0
    fetch_success = 0
    fetch_failed = 0
    evidence_items = 0
    total_result_chars = len(raw)

    fetched_prefix = re.compile(r"^\[(?:Fetched|RunScoped) (\d+)\]")
    legacy_prefix = re.compile(r"^\[\d+\]")

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue

        # Count hits: "共 N 条结果" or "返回 N 条"
        if "条结果" in line_s or "条命中" in line_s:
            nums = re.findall(r"(\d+)\s*条", line_s)
            if nums:
                hit_count = max(hit_count, int(nums[0]))

        # Count fetch status
        if "抓取成功" in line_s or "fetch_ok" in line_s.lower():
            fetch_success += 1
        elif "抓取失败" in line_s or "fetch_failed" in line_s.lower():
            fetch_failed += 1

        # Count evidence items: lines starting with [Fetched N] / [RunScoped N]
        # (current format) or legacy [N] (kept for backward compatibility).
        m = fetched_prefix.match(line_s)
        if m:
            evidence_items += 1
            fetch_success += 1
            hit_count = max(hit_count, int(m.group(1)))
        elif legacy_prefix.match(line_s) and len(line_s) > 8:
            evidence_items += 1

    # Estimate from raw text if explicit counts not found
    if hit_count == 0:
        # Fallback: count lines starting with [Fetched N] / [RunScoped N]
        hit_count = len([l for l in lines if fetched_prefix.match(l.strip())])
        # Or legacy [N] lines
        if hit_count == 0:
            hit_count = len([l for l in lines if legacy_prefix.match(l.strip())])
        # Or count "来源:" markers
        if hit_count == 0:
            hit_count = sum(1 for l in lines if "来源:" in l or "source:" in l.lower())

    result_count = hit_count
    fetch_total = fetch_success + fetch_failed
    fetch_success_rate = fetch_success / max(1, fetch_total)
    effective_evidence_rate = evidence_items / max(1, result_count)

    # Provider detection
    providers = _detect_providers(raw)

    return {
        "result_count": result_count,
        "fetch_success": fetch_success,
        "fetch_failed": fetch_failed,
        "fetch_success_rate": round(fetch_success_rate, 3),
        "evidence_items": evidence_items,
        "effective_evidence_rate": round(effective_evidence_rate, 3),
        "total_chars": total_result_chars,
        "providers": providers,
    }


def _detect_providers(raw: str) -> dict[str, int]:
    """Detect which search providers contributed results."""
    counts: dict[str, int] = {}
    lower = raw.lower()

    provider_markers = {
        "duckduckgo": ["duckduckgo", "ddgs"],
        "bing": ["bing.com", "bing search"],
        "google": ["google.com", "google search", "google cse"],
        "serpapi": ["serpapi", "serp_api"],
    }

    for provider, markers in provider_markers.items():
        for marker in markers:
            if marker in lower:
                counts[provider] = counts.get(provider, 0) + 1

    return counts


def evaluate_batch(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics across all queries."""
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") != "success"]

    hit_rate = len(successful) / max(1, len(results))
    elapsed_times = [r.get("elapsed_seconds", 0) for r in successful]

    fetch_rates = [r.get("fetch_success_rate", 0) for r in successful]
    evidence_rates = [r.get("effective_evidence_rate", 0) for r in successful]

    # Provider distribution
    provider_totals: dict[str, int] = {}
    for r in successful:
        for p, c in (r.get("providers") or {}).items():
            provider_totals[p] = provider_totals.get(p, 0) + c

    # Mean result count
    result_counts = [r.get("result_count", 0) for r in successful]

    return {
        "query_count": len(results),
        "success_count": len(successful),
        "failed_count": len(failed),
        "hit_rate": round(hit_rate, 3),
        "mean_elapsed_seconds": round(statistics.mean(elapsed_times), 2) if elapsed_times else 0,
        "median_elapsed_seconds": round(statistics.median(elapsed_times), 2) if elapsed_times else 0,
        "mean_result_count": round(statistics.mean(result_counts), 1) if result_counts else 0,
        "mean_fetch_success_rate": round(statistics.mean(fetch_rates), 3) if fetch_rates else 0,
        "mean_effective_evidence_rate": round(statistics.mean(evidence_rates), 3) if evidence_rates else 0,
        "provider_distribution": provider_totals,
    }


def write_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "web_search_eval.json"
    md_path = out_dir / "web_search_eval.md"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    agg = payload["aggregate"]
    lines = [
        "# Web Search Quality Evaluation",
        "",
        f"**Queries**: {agg['query_count']}  |  "
        f"**Success**: {agg['success_count']}  |  "
        f"**Failed**: {agg['failed_count']}  |  "
        f"**Hit rate**: {agg['hit_rate']:.1%}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Hit rate | {agg['hit_rate']:.1%} |",
        f"| Mean result count | {agg['mean_result_count']:.1f} |",
        f"| Mean fetch success rate | {agg['mean_fetch_success_rate']:.1%} |",
        f"| Mean effective evidence rate | {agg['mean_effective_evidence_rate']:.1%} |",
        f"| Mean elapsed | {agg['mean_elapsed_seconds']:.1f}s |",
        f"| Median elapsed | {agg['median_elapsed_seconds']:.1f}s |",
        "",
        "## Provider Distribution",
        "",
        "| Provider | Queries detected |",
        "|---|---|",
        *[f"| {p} | {c} |" for p, c in sorted(agg.get("provider_distribution", {}).items())],
        "",
        "## Per-Query Details",
        "",
        "| ID | Query | Results | Fetch% | Evidence% | Time |",
        "|---|---:|---:|---:|---:|",
    ]

    for r in payload["results"]:
        q_short = r["query"][:50]
        lines.append(
            f"| {r.get('id', '')} | {q_short} | "
            f"{r.get('result_count', '—')} | "
            f"{r.get('fetch_success_rate', '—')} | "
            f"{r.get('effective_evidence_rate', '—')} | "
            f"{r.get('elapsed_seconds', '—')}s |"
        )
    lines.append("")

    # Annotations section (placeholder for manual relevance ratings)
    lines.extend([
        "## Manual Relevance Ratings (1-3)",
        "",
        "| ID | Query | Result Relevance (1-3) | Notes |",
        "|---|---:|---|",
    ])
    for r in payload["results"]:
        q_short = r["query"][:50]
        lines.append(f"| {r.get('id', '')} | {q_short} | _TBD_ | |")
    lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Web search quality evaluation.")
    parser.add_argument("--queries", default="data/web_eval_queries.yaml")
    parser.add_argument("--out-dir", default="reports/eval/web")
    parser.add_argument("--depth", choices=("quick", "standard", "deep"), default="standard")
    parser.add_argument("--k", type=int, default=18, help="Max queries to run (default 18)")
    parser.add_argument("--timeout", type=int, default=30, help="Per-query timeout seconds")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.workbench", override=False)

    from conflux import config
    from conflux.config import load as load_config
    from conflux.model_factory import create_research_models
    from conflux.research_modes import resolve_research_profile
    from conflux.tools.web import create_web_tool

    load_config()
    profile = resolve_research_profile(args.depth)
    models, model_trace = create_research_models(args.depth)
    web_tool = create_web_tool(profile)

    items = load_queries(ROOT / args.queries)[: args.k]
    deadline_at = time.time() + (len(items) * args.timeout * 2)

    print(f"Web search eval: {len(items)} queries, depth={args.depth}, per-query timeout={args.timeout}s")
    print(f"Model: {model_trace.get('roles', {}).get('reranker', {}).get('model', 'N/A')}")
    print()

    results: list[dict[str, Any]] = []
    for item in items:
        qid = item.get("id", "?")
        print(f"  [{qid}] {item['query'][:60]} ... ", end="", flush=True)
        result = run_one_query(item, web_tool, deadline_at)
        results.append(result)
        print(f"{result.get('result_count', 0)} results, {result['elapsed_seconds']}s")
        time.sleep(0.5)  # rate-limit between queries

    aggregate = evaluate_batch(results)
    payload = {
        "depth": args.depth,
        "model_trace": model_trace,
        "aggregate": aggregate,
        "results": results,
    }

    md_path, json_path = write_outputs(payload, ROOT / args.out_dir)
    print(f"\nMarkdown: {md_path}")
    print(f"JSON: {json_path}")
    print(f"\nHit rate: {aggregate['hit_rate']:.1%} | "
          f"Mean results: {aggregate['mean_result_count']:.1f} | "
          f"Fetch success: {aggregate['mean_fetch_success_rate']:.1%} | "
          f"Evidence rate: {aggregate['mean_effective_evidence_rate']:.1%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
