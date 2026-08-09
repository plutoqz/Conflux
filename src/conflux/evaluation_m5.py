"""M5 evaluation manifest, strategy comparison, and evidence audit."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping


M5_SCHEMA_VERSION = "conflux-m5-evaluation-v1"


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_manifest(manifest: Mapping[str, Any], *, root: str | Path = ".") -> dict[str, Any]:
    base = Path(root).resolve()
    strategies = [_strategy_row(item, base) for item in manifest.get("strategies") or []]
    r3 = _r3_row(manifest.get("r3") or {}, base)
    extensions = [dict(item) for item in manifest.get("extensions") or []]
    debt = dict(manifest.get("debt") or {})
    debt_artifacts = {
        key: {
            "path": str((base / str(value)).resolve()),
            "sha256": file_sha256(base / str(value)),
        }
        for key, value in debt.items()
        if key.endswith("_artifact") and value
    }
    return {
        "schema_version": M5_SCHEMA_VERSION,
        "dataset_id": str(manifest.get("dataset_id") or ""),
        "evidence_scope": str(manifest.get("evidence_scope") or "recorded_and_replay"),
        "strategies": strategies,
        "r3": r3,
        "extensions": extensions,
        "debt": debt,
        "debt_artifacts": debt_artifacts,
        "checks": {
            "strategy_kinds": sorted({item["kind"] for item in strategies}),
            "four_strategy_matrix_complete": {
                "deterministic", "llm_batch", "deep_review", "hybrid"
            }.issubset({item["kind"] for item in strategies}),
            "all_artifacts_hashed": all(item["artifact_sha256"] for item in strategies),
            "all_failures_structured": all(item["failure_semantics"] == "unreviewed_or_needs_review" for item in strategies),
            "complementary_extensions": _extensions_complementary(extensions),
            "r3_uses_current_path": bool(r3.get("current_v2_v3_path")),
            "debt_evidence_hashed": len(debt_artifacts) >= 2 and all(item["sha256"] for item in debt_artifacts.values()),
        },
    }


def _strategy_row(spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    artifact = (root / str(spec.get("artifact") or "")).resolve()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    result_rows = [item for item in payload.get("results") or [] if isinstance(item, Mapping)]
    representative = result_rows[0] if result_rows else payload
    retrieval = representative.get("retrieval") or {}
    cost = representative.get("cost") or {}
    run_count = int(payload.get("run_count") or len(payload.get("results") or []) or 1)
    configs = [
        json.loads((root / str(item)).read_text(encoding="utf-8"))
        for item in spec.get("configs") or []
    ]
    return {
        "id": str(spec.get("id") or ""),
        "kind": str(spec.get("kind") or ""),
        "domain": str(spec.get("domain") or ""),
        "artifact": str(artifact),
        "artifact_sha256": file_sha256(artifact),
        "run_count": run_count,
        "quality": {
            "ndcg_at_10": _metric(retrieval, "ndcg_at_10"),
            "mrr": _metric(retrieval, "mrr"),
            "strong_recall_at_20": _metric(retrieval, "strong_recall_at_20"),
            "strong_success_at_1": _success_metric(retrieval, "strong_success_at_1"),
        },
        "cost": {
            "semantic_review_tokens": _metric(cost, "semantic_review_tokens") or _median_config(configs, "semantic_review_tokens"),
            "semantic_review_calls": _metric(cost, "semantic_review_calls") or _median_config(configs, "semantic_review_calls"),
            "estimated_cost_usd": spec.get("estimated_cost_usd"),
            "cost_available": spec.get("estimated_cost_usd") is not None,
        },
        "latency": {
            "elapsed_seconds_median": (
                _median_config(configs, "elapsed_seconds")
                or (round(float(cost.get("elapsed_seconds")), 4) if cost.get("elapsed_seconds") is not None else None)
            ),
        },
        "failures": {
            "semantic_review_failed_median": _median_config(configs, "semantic_review_failed"),
            "needs_review_visible": bool(spec.get("needs_review_visible", True)),
        },
        "failure_semantics": str(spec.get("failure_semantics") or "unreviewed_or_needs_review"),
        "notes": [str(item) for item in spec.get("notes") or []],
    }


def _r3_row(spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    artifact = (root / str(spec.get("artifact") or "")).resolve()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    conditions = []
    for item in payload.get("conditions") or []:
        aggregate = item.get("aggregate") or {}
        conditions.append({
            "variant": item.get("variant"),
            "policy": item.get("baseline_policy") or {},
            "verification_accuracy": ((aggregate.get("verification") or {}).get("mean_verdict_accuracy")),
            "citation_correctness": ((aggregate.get("answer") or {}).get("mean_citation_correctness")),
            "latency_ms": ((aggregate.get("runtime") or {}).get("mean_latency_ms")),
            "tokens": ((aggregate.get("runtime") or {}).get("mean_total_tokens")),
        })
    return {
        "artifact": str(artifact),
        "artifact_sha256": file_sha256(artifact),
        "fixture_type": payload.get("fixture_type"),
        "current_v2_v3_path": bool(spec.get("current_v2_v3_path", True)),
        "conditions": conditions,
        "interpretation": payload.get("interpretation"),
        "live_quality_claim": False,
    }


def _metric(container: Mapping[str, Any], key: str) -> float | None:
    value = container.get(key)
    if isinstance(value, Mapping):
        value = value.get("median")
    if value is None:
        results = container.get("results")
        if isinstance(results, list):
            values = [
                float((item.get("retrieval") or {}).get(key))
                for item in results
                if (item.get("retrieval") or {}).get(key) is not None
            ]
            return round(float(statistics.median(values)), 4) if values else None
        return None
    return round(float(value), 4)


def _success_metric(container: Mapping[str, Any], key: str) -> dict[str, int] | None:
    value = container.get(key)
    if isinstance(value, Mapping):
        return {"count": int(value.get("count") or 0), "total": int(value.get("total") or 0)}
    return None


def _median_config(configs: Iterable[Mapping[str, Any]], key: str) -> float | None:
    values = [float(item[key]) for item in configs if item.get(key) is not None]
    return round(float(statistics.median(values)), 4) if values else None


def _extensions_complementary(extensions: list[dict[str, Any]]) -> bool:
    types = {str(item.get("type") or "") for item in extensions if item.get("contract_passed")}
    return "data_source" in types and bool(types & {"workflow", "evaluator", "renderer"})


def render_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# M5 LLM Review Evaluation",
        "",
        f"- Dataset: {result.get('dataset_id')}",
        f"- Evidence scope: {result.get('evidence_scope')}",
        "",
        "| Strategy | Domain | Runs | nDCG@10 | Strong recall@20 | Tokens | Latency(s) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in result.get("strategies") or []:
        lines.append(
            f"| {row['id']} | {row['domain']} | {row['run_count']} | "
            f"{row['quality']['ndcg_at_10']} | {row['quality']['strong_recall_at_20']} | "
            f"{row['cost']['semantic_review_tokens']} | {row['latency']['elapsed_seconds_median']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Recorded and replay artifacts support configuration comparison, not a new live-provider quality claim.",
        "- Missing provider pricing remains `cost_available=false`; token counts are reported without inventing USD cost.",
        "- Review failures must remain visible as `unreviewed` or `needs_review`.",
        "- R3 uses the current V2/V3 B2/B3/B4 path; the controlled replay isolates workflow behavior.",
        "",
        "## Checks",
        "",
    ])
    lines.extend(f"- {key}: {value}" for key, value in (result.get("checks") or {}).items())
    return "\n".join(lines) + "\n"
