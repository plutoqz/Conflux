"""P2 Paper Radar evaluation: labeled-set metrics for radar runs.

Covers the P2 exit-criteria metrics: recall@k, precision@k, duplicate
handling rate, ungrounded-analysis rate, token usage, latency, and
source error rate.  Labels follow the conflux-p2-radar-labels-v1 schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

P2_LABELS_SCHEMA_VERSION = "conflux-p2-radar-labels-v1"


def load_p2_labels(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {path}: {line!r}")
        rows.append(payload)
    return rows


def _as_run(run: Any) -> dict[str, Any]:
    if hasattr(run, "model_dump"):
        return run.model_dump()
    if isinstance(run, dict):
        return run
    raise TypeError("run must be a RadarRunResult or its dict representation")


def _links(run: dict[str, Any]) -> list[dict[str, Any]]:
    return list(run.get("links") or [])


def _stats(run: dict[str, Any]) -> dict[str, Any]:
    stats = run.get("stats") or {}
    if not isinstance(stats, dict):
        stats = stats.model_dump() if hasattr(stats, "model_dump") else {}
    return stats


def _suggestions(run: dict[str, Any]) -> list[dict[str, Any]]:
    return list(run.get("suggestions") or [])


def _paper_id(link: dict[str, Any]) -> str:
    identity = link.get("paper_identity") or {}
    return str(identity.get("canonical_id") or link.get("paper_id") or "")


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def evaluate_p2_run(run: Any, labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Score one radar run against a labeled set.

    ``run`` may be a RadarRunResult or its model_dump() dict (keys: links,
    stats, suggestions).  Labels use relevance >= 2 as the positive class.
    """
    run = _as_run(run)
    stats = _stats(run)
    links = _links(run)
    suggestions = _suggestions(run)

    ranked_links = sorted(links, key=lambda link: -float(link.get("relevance") or 0.0))
    link_ids = [_paper_id(link) for link in ranked_links]
    relevant_ids = {
        str(label.get("paper_id") or "")
        for label in labels
        if int(label.get("relevance") or 0) >= 2
    }
    relevant_ids.discard("")

    cutoffs = [1, 5, 10]
    retrieval: dict[str, Any] = {}
    for k in cutoffs:
        top_k = link_ids[:k]
        if not top_k:
            retrieval[f"recall_at_{k}"] = None
            retrieval[f"precision_at_{k}"] = None
            continue
        hits = sum(1 for paper_id in top_k if paper_id in relevant_ids)
        retrieval[f"recall_at_{k}"] = (
            round(hits / len(relevant_ids), 4) if relevant_ids else None
        )
        retrieval[f"precision_at_{k}"] = round(hits / len(top_k), 4)
    retrieval["relevant_labeled_count"] = len(relevant_ids)
    retrieval["linked_count"] = len(link_ids)
    retrieval["linked_relevant_count"] = sum(
        1 for paper_id in link_ids if paper_id in relevant_ids
    )

    total_candidates = int(stats.get("total_candidates") or 0)
    after_dedup = int(stats.get("after_dedup") or 0)
    dedup_rate = (
        round(1 - after_dedup / total_candidates, 4) if total_candidates else None
    )

    suggestion_count = len(suggestions)
    ungrounded = [
        item for item in suggestions
        if not [ref for ref in item.get("evidence_refs") or [] if str(ref).strip()]
    ]
    ungrounded_rate = (
        round(len(ungrounded) / suggestion_count, 4) if suggestion_count else None
    )

    sources_used = [str(item) for item in stats.get("sources_used") or []]
    failed_sources = [str(item) for item in stats.get("failed_sources") or []]
    source_total = len(sources_used) + len(failed_sources)
    source_error_rate = (
        round(len(failed_sources) / source_total, 4) if source_total else None
    )

    query_stats = [item for item in stats.get("query_stats") or [] if isinstance(item, dict)]
    per_track: dict[str, dict[str, Any]] = {}
    for entry in query_stats:
        track_id = str(entry.get("track_id") or "")
        bucket = per_track.setdefault(track_id, {"query_count": 0, "failed_count": 0, "candidate_count": 0})
        bucket["query_count"] += 1
        bucket["candidate_count"] += int(entry.get("candidate_count") or 0)
        if entry.get("failed"):
            bucket["failed_count"] += 1

    return {
        "schema_version": P2_LABELS_SCHEMA_VERSION,
        "retrieval": retrieval,
        "queries": {
            "query_count": len(query_stats),
            "failed_query_count": sum(1 for item in query_stats if item.get("failed")),
            "by_query": query_stats,
            "by_track": per_track,
        },
        "duplicate_handling": {
            "total_candidates": total_candidates,
            "after_dedup": after_dedup,
            "dedup_rate": dedup_rate,
        },
        "analysis": {
            "suggestion_count": suggestion_count,
            "ungrounded_suggestion_count": len(ungrounded),
            "ungrounded_analysis_rate": ungrounded_rate,
            "llm_fallback_count": int(stats.get("llm_fallback_count") or 0),
            "needs_review_count": int(stats.get("needs_review") or 0),
        },
        "cost": {
            "llm_total_tokens": int(stats.get("llm_total_tokens") or 0),
            "semantic_review_tokens": int(stats.get("semantic_review_tokens") or 0),
            "semantic_review_calls": int(stats.get("semantic_review_calls") or 0),
            "semantic_review_failed": int(stats.get("semantic_review_failed") or 0),
            "llm_elapsed_ms": int(stats.get("llm_elapsed_ms") or 0),
            "elapsed_seconds": stats.get("elapsed_seconds"),
            "cost_available": False,
        },
        "sources": {
            "sources_used": sources_used,
            "failed_sources": failed_sources,
            "source_error_rate": source_error_rate,
        },
    }


def aggregate_p2_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval_rows = [item["retrieval"] for item in results]
    analysis_rows = [item["analysis"] for item in results]
    return {
        "run_count": len(results),
        "retrieval": {
            f"mean_recall_at_{k}": _mean(
                [row.get(f"recall_at_{k}") for row in retrieval_rows if row.get(f"recall_at_{k}") is not None]
            )
            for k in (1, 5, 10)
        } | {
            f"mean_precision_at_{k}": _mean(
                [row.get(f"precision_at_{k}") for row in retrieval_rows if row.get(f"precision_at_{k}") is not None]
            )
            for k in (1, 5, 10)
        },
        "analysis": {
            "mean_ungrounded_analysis_rate": _mean(
                [row.get("ungrounded_analysis_rate") for row in analysis_rows if row.get("ungrounded_analysis_rate") is not None]
            ),
            "total_needs_review": sum(int(row.get("needs_review_count") or 0) for row in analysis_rows),
            "total_llm_fallback": sum(int(row.get("llm_fallback_count") or 0) for row in analysis_rows),
        },
    }
