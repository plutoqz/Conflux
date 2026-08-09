"""Offline scoring for the §8.10 Retrieval/Verification/Answer Gold assets."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable


GOLD_SCHEMA_VERSION = "conflux-v2-gold-v1"
RETRIEVAL_GRADES = {0, 1, 2, 3}
VERIFICATION_VERDICTS = {"supports", "contradicts", "insufficient", "uncertain"}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _read_gold_rows(root: Path, pattern: str) -> list[dict[str, Any]]:
    paths = sorted(root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no Gold asset matches {root / pattern}")
    return [row for path in paths for row in _read_jsonl(path)]


def load_gold_bundle(gold_dir: str | Path) -> dict[str, Any]:
    root = Path(gold_dir)
    bundle = {
        "manifest": _read_json(root / "manifest.json"),
        "retrieval": _read_gold_rows(root, "retrieval_gold*.jsonl"),
        "verification": _read_gold_rows(root, "verification_gold*.jsonl"),
        "answer": _read_gold_rows(root, "answer_gold*.jsonl"),
    }
    errors = validate_gold_bundle(bundle)
    if errors:
        raise ValueError("invalid Gold bundle:\n- " + "\n- ".join(errors))
    return bundle


def validate_gold_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest = bundle.get("manifest")
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema_version") != GOLD_SCHEMA_VERSION:
        errors.append("manifest.schema_version is unsupported")

    by_case: dict[str, dict[str, int]] = {}
    for row in bundle.get("retrieval") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            errors.append("retrieval row is missing case_id")
            continue
        seen_subquestions: set[str] = set()
        for subquestion in row.get("subquestions") or []:
            subquestion_id = str(subquestion.get("subquestion_id") or "")
            if not subquestion_id or subquestion_id in seen_subquestions:
                errors.append(f"retrieval {case_id} has invalid or duplicate subquestion_id")
                continue
            seen_subquestions.add(subquestion_id)
            labels = subquestion.get("evidence") or []
            for label in labels:
                evidence_id = str(label.get("evidence_id") or "")
                grade = label.get("relevance_grade")
                if not evidence_id:
                    errors.append(f"retrieval {case_id}/{subquestion_id} has missing evidence_id")
                if grade not in RETRIEVAL_GRADES:
                    errors.append(f"retrieval {case_id}/{subquestion_id} has invalid relevance_grade")
            by_case.setdefault(case_id, {})[subquestion_id] = len(labels)

    retrieval_cases = set(by_case)
    for name in ("verification", "answer"):
        for row in bundle.get(name) or []:
            case_id = str(row.get("case_id") or "")
            if not case_id:
                errors.append(f"{name} row is missing case_id")
            elif case_id not in retrieval_cases:
                errors.append(f"{name} case has no retrieval Gold: {case_id}")

            if name == "verification":
                for item in row.get("subquestions") or []:
                    for label in item.get("evidence") or []:
                        if label.get("verdict") not in VERIFICATION_VERDICTS:
                            errors.append(f"verification {case_id} has invalid verdict")
    return errors


def _dcg(grades: Iterable[int]) -> float:
    return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))


def _ndcg(grades: list[int], *, cutoff: int) -> float | None:
    if not any(grades):
        return None
    observed = _dcg(grades[:cutoff])
    ideal = _dcg(sorted(grades, reverse=True)[:cutoff])
    return round(observed / ideal, 4) if ideal else None


def _records(summary: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = summary.get("ledger_snapshot") or {}
    return [item for item in snapshot.get("records") or [] if isinstance(item, dict)]


def _claims(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in summary.get("claim_records") or [] if isinstance(item, dict)]


def _rank_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Rank evidence without treating concurrent ledger append order as rank."""

    explicit_ranked = [item for item in records if item.get("retrieval_rank") is not None]
    if explicit_ranked:
        return sorted(records, key=lambda item: int(item.get("retrieval_rank") or 10**9)), "retrieval_rank"
    if any(item.get("claim_fitness") is not None for item in records):
        ranked = sorted(
            enumerate(records),
            key=lambda pair: (-float(pair[1].get("claim_fitness") or 0.0), pair[0]),
        )
        return [item for _, item in ranked], "claim_fitness"
    return records, "ledger_order_unranked"


def _mean(values: Iterable[float | int | None]) -> float | None:
    usable = [float(value) for value in values if value is not None]
    return round(sum(usable) / len(usable), 4) if usable else None


def _p95(values: Iterable[float | int | None]) -> float | None:
    usable = sorted(float(value) for value in values if value is not None)
    if not usable:
        return None
    index = max(0, math.ceil(len(usable) * 0.95) - 1)
    return round(usable[index], 2)


def score_run(case_id: str, summary: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    retrieval_case = next((item for item in bundle["retrieval"] if item.get("case_id") == case_id), None)
    verification_case = next((item for item in bundle["verification"] if item.get("case_id") == case_id), None)
    answer_case = next((item for item in bundle["answer"] if item.get("case_id") == case_id), None)
    if not retrieval_case or not verification_case or not answer_case:
        raise KeyError(f"Gold case is incomplete: {case_id}")

    records = _records(summary)
    primary_records = [item for item in records if str(item.get("visibility") or "primary") == "primary"]
    retrieval_scores: list[dict[str, Any]] = []
    for subquestion in retrieval_case.get("subquestions") or []:
        subquestion_id = str(subquestion["subquestion_id"])
        labels = {
            str(item["evidence_id"]): int(item["relevance_grade"])
            for item in subquestion.get("evidence") or []
        }
        retrieved = [
            item for item in primary_records
            if str(item.get("subquestion_id") or "") == subquestion_id
        ]
        retrieved, ranking_source = _rank_records(retrieved)
        grades = [labels.get(str(item.get("evidence_id") or ""), 0) for item in retrieved]
        cutoff = max(1, int(subquestion.get("k") or 5))
        direct_grade_min = max(1, int(subquestion.get("direct_grade_min") or 3))
        positive_count = sum(1 for grade in labels.values() if grade > 0)
        direct_positive_count = sum(1 for grade in labels.values() if grade >= direct_grade_min)
        retrieved_positive = sum(1 for grade in grades[:cutoff] if grade > 0)
        retrieved_direct_positive = sum(1 for grade in grades[:cutoff] if grade >= direct_grade_min)
        retrieval_scores.append({
            "subquestion_id": subquestion_id,
            "retrieved_count": len(retrieved),
            "ranking_source": ranking_source,
            "retrieved_evidence_ids": [str(item.get("evidence_id") or "") for item in retrieved],
            "unlabeled_retrieved_count": sum(
                1 for item in retrieved if str(item.get("evidence_id") or "") not in labels
            ),
            "irrelevant_at_k": sum(1 for grade in grades[:cutoff] if grade == 0),
            "recall_at_k": round(retrieved_positive / positive_count, 4) if positive_count else None,
            "direct_recall_at_k": (
                round(retrieved_direct_positive / direct_positive_count, 4)
                if direct_positive_count else None
            ),
            "ndcg_at_k": _ndcg(grades, cutoff=cutoff),
            "expected_no_evidence": bool(subquestion.get("expected_no_evidence", False)),
        })

    claims = _claims(summary)
    expected_claims = [item for item in answer_case.get("expected_claims") or [] if isinstance(item, dict)]
    expected_claim_ids = {str(item.get("claim_id") or "") for item in expected_claims}
    generated_claim_ids = {str(item.get("claim_id") or "") for item in claims}
    claim_coverage = (
        round(len(expected_claim_ids & generated_claim_ids) / len(expected_claim_ids), 4)
        if expected_claim_ids else None
    )

    expected = answer_case.get("expected") or {}
    verification_expected = {
        str(item.get("subquestion_id") or ""): item
        for item in verification_case.get("subquestions") or []
    }
    abstention_expected = all(
        str(item.get("expected_claim_policy") or "") == "abstain"
        for item in verification_expected.values()
    )
    abstention_correct = len(claims) == 0 if abstention_expected else None

    verification_labels = [
        label
        for item in verification_expected.values()
        for label in item.get("evidence") or []
        if isinstance(label, dict)
    ]
    expected_verdicts = {
        str(label.get("evidence_id") or ""): str(label.get("verdict") or "")
        for label in verification_labels
        if label.get("score_verdict", True) is not False
    }
    observed_verdicts = [
        (str(evidence_id), str((claim.get("verification_result") or {}).get("verdict") or ""))
        for claim in claims
        for evidence_id in claim.get("evidence_ids") or []
        if str(evidence_id) in expected_verdicts
    ]
    verification_accuracy = (
        round(
            sum(predicted == expected_verdicts[evidence_id] for evidence_id, predicted in observed_verdicts)
            / len(observed_verdicts),
            4,
        )
        if observed_verdicts else None
    )

    valid_citation_count = sum(
        1 for claim in claims
        for ref in (claim.get("generation_attribution") or {}).get("citation_refs") or []
        if str(ref).strip()
    )
    citation_correctness = None if not claims else (
        1.0 if int(summary.get("invalid_citation_count") or 0) == 0 else 0.0
    )

    answer_score = {
        "expected_run_status": expected.get("run_status"),
        "actual_run_status": summary.get("run_status"),
        "run_status_match": (
            True if expected.get("run_status") in (None, "")
            else str(summary.get("run_status") or "") == str(expected.get("run_status"))
        ),
        "confidence_match": (
            True if expected.get("confidence") in (None, "")
            else str(summary.get("confidence") or "") == str(expected.get("confidence"))
        ),
        "factcheck_match": (
            True if expected.get("factcheck_status") in (None, "")
            else str(summary.get("factcheck_status") or "") == str(expected.get("factcheck_status"))
        ),
        "generated_claim_count": len(claims),
        "claim_coverage": claim_coverage,
        "abstention_correct": abstention_correct,
        "valid_citation_count": valid_citation_count,
        "citation_correctness": citation_correctness,
    }

    budget = summary.get("budget_consumed") or {}
    total_tokens = int(budget.get("input_tokens") or 0) + int(budget.get("output_tokens") or 0)
    return {
        "case_id": case_id,
        "query": summary.get("query") or retrieval_case.get("query") or "",
        "retrieval": retrieval_scores,
        "verification": {
            "expected_claim_policies": {
                key: value.get("expected_claim_policy")
                for key, value in verification_expected.items()
            },
            "generated_claim_count": len(claims),
            "abstention_correct": abstention_correct,
            "observed_verdict_count": len(observed_verdicts),
            "missing_scored_evidence_ids": sorted(
                set(expected_verdicts) - {evidence_id for evidence_id, _ in observed_verdicts}
            ),
            "unscored_label_count": sum(
                1 for label in verification_labels if label.get("score_verdict", True) is False
            ),
            "verdict_accuracy": verification_accuracy,
        },
        "answer": answer_score,
        "runtime": {
            "run_status": summary.get("run_status"),
            "confidence": summary.get("confidence"),
            "elapsed_ms": summary.get("elapsed_ms"),
            "input_tokens": int(budget.get("input_tokens") or 0),
            "output_tokens": int(budget.get("output_tokens") or 0),
            "total_tokens": total_tokens,
            "estimated_cost_usd": summary.get("estimated_cost"),
        },
    }


def aggregate_scores(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(results)
    retrieval_rows = [row for item in items for row in item.get("retrieval") or []]
    answer_rows = [item.get("answer") or {} for item in items]
    runtime_rows = [item.get("runtime") or {} for item in items]
    return {
        "run_count": len(items),
        "retrieval": {
            "mean_recall_at_k": _mean(row.get("recall_at_k") for row in retrieval_rows),
            "mean_context_recall_at_k": _mean(row.get("recall_at_k") for row in retrieval_rows),
            "mean_direct_recall_at_k": _mean(row.get("direct_recall_at_k") for row in retrieval_rows),
            "mean_ndcg_at_k": _mean(row.get("ndcg_at_k") for row in retrieval_rows),
            "mean_irrelevant_at_k": _mean(row.get("irrelevant_at_k") for row in retrieval_rows),
            "unlabeled_retrieved_count": sum(
                int(row.get("unlabeled_retrieved_count") or 0) for row in retrieval_rows
            ),
        },
        "verification": {
            "abstention_correct_count": sum(
                1 for row in answer_rows if row.get("abstention_correct") is True
            ),
            "abstention_evaluable_count": sum(
                1 for row in answer_rows if row.get("abstention_correct") is not None
            ),
            "mean_verdict_accuracy": _mean(
                item.get("verification", {}).get("verdict_accuracy") for item in items
            ),
        },
        "answer": {
            "mean_claim_coverage": _mean(row.get("claim_coverage") for row in answer_rows),
            "mean_citation_correctness": _mean(row.get("citation_correctness") for row in answer_rows),
            "run_status_match_count": sum(1 for row in answer_rows if row.get("run_status_match")),
            "confidence_match_count": sum(1 for row in answer_rows if row.get("confidence_match")),
        },
        "runtime": {
            "p95_latency_ms": _p95(row.get("elapsed_ms") for row in runtime_rows),
            "mean_latency_ms": _mean(row.get("elapsed_ms") for row in runtime_rows),
            "mean_total_tokens": _mean(row.get("total_tokens") for row in runtime_rows),
            "cost_available": all(row.get("estimated_cost_usd") is not None for row in runtime_rows),
        },
    }


def score_runs(
    run_summaries: dict[str, dict[str, Any]],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    results = [score_run(case_id, summary, bundle) for case_id, summary in run_summaries.items()]
    return {
        "schema_version": GOLD_SCHEMA_VERSION,
        "results": results,
        "aggregate": aggregate_scores(results),
    }


# ============================================================
# Query-level semantic Gold (conflux-v2-gold-semantic-v1)
# Reusable across runs: evidence is matched by semantics instead
# of run-bound evidence ids or subquestion plans.
# ============================================================

SEMANTIC_SCHEMA_VERSION = "conflux-v2-gold-semantic-v1"


def load_semantic_gold(gold_dir: str | Path) -> list[dict[str, Any]]:
    """Load all semantic gold assets from <gold_dir>/semantic/*.semantic.json."""
    root = Path(gold_dir)
    assets: list[dict[str, Any]] = []
    paths = sorted((root / "semantic").glob("*.semantic.json"))
    if not paths:
        raise FileNotFoundError(f"no semantic Gold assets match {root / 'semantic' / '*.semantic.json'}")
    for path in paths:
        payload = _read_json(path)
        if payload.get("schema_version") != SEMANTIC_SCHEMA_VERSION:
            raise ValueError(f"unsupported semantic Gold schema: {path}")
        assets.append(payload)
    return assets


def _normalize_for_match(text: Any) -> str:
    normalized = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", str(text or ""))
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _evidence_text(record: dict[str, Any]) -> str:
    return _normalize_for_match(record.get("verbatim_quote") or record.get("claim") or "")


def _match_evidence(
    record: dict[str, Any],
    aspect: dict[str, Any],
    negatives: list[str],
) -> tuple[int, list[str], list[str], list[str]]:
    """Return (grade, keyword_hits, positive_hits, negative_hits).

    grade 0 = negative/off-domain; 2 = keyword-only partial relevance;
    3 = positive semantic (or keyword set) direct relevance.
    """
    text = _evidence_text(record)
    neg_hits = [item for item in negatives if item.casefold() in text]
    if neg_hits:
        return 0, [], [], neg_hits
    kw_hits = [item for item in aspect.get("keywords") or [] if item.casefold() in text]
    pos_hits = [
        item for item in aspect.get("positive_semantics") or []
        if _normalize_for_match(item) in text
    ]
    if pos_hits:
        return 3, kw_hits, pos_hits, []
    if kw_hits:
        return 2, kw_hits, [], []
    return 0, [], [], []


def _align_subquestion(sub_questions: list[dict[str, Any]], aspect: dict[str, Any]) -> dict[str, Any] | None:
    """Pick the run subquestion with the most keyword/positive overlap (>=1 hit)."""
    best: dict[str, Any] | None = None
    best_score = 0
    for sq in sub_questions or []:
        question = _normalize_for_match(sq.get("question") or "")
        score = sum(1 for key in aspect.get("keywords") or [] if key.casefold() in question)
        score += sum(
            1 for item in aspect.get("positive_semantics") or []
            if _normalize_for_match(item) in question
        )
        if score > best_score:
            best_score = score
            best = sq
    return best if best_score >= 1 else None


def _claim_records(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in summary.get("claim_records") or [] if isinstance(item, dict)]


def _records_by_id(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("evidence_id") or ""): item
        for item in summary.get("ledger_snapshot", {}).get("records") or []
        if isinstance(item, dict)
    }


def _primary_by_subquestion(summary: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in summary.get("ledger_snapshot", {}).get("records") or []:
        if not isinstance(item, dict) or str(item.get("visibility") or "primary") != "primary":
            continue
        grouped.setdefault(str(item.get("subquestion_id") or ""), []).append(item)
    return grouped


def _query_plan_from_trace(summary: dict[str, Any]) -> list[dict[str, Any]]:
    trace_path = str(summary.get("trace_path") or "")
    if not trace_path or not Path(trace_path).exists():
        return []
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("stage") == "v2_run_summary":
            return list((event.get("metadata") or {}).get("query_plan") or [])
    return []


def _claim_aspect_hits(
    claim: dict[str, Any],
    aspect: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return (exact_positive_hits, keyword_hits) for one claim against an aspect.

    Exact positive semantics are the strongest evidence of coverage, but
    generated claims often express the same meaning with different wording
    (especially cross-language).  Keyword hits are therefore counted as
    coverage too, while both lists remain available for audit.
    """

    text = _normalize_for_match(claim.get("text") or "")
    exact = [
        item for item in aspect.get("positive_semantics") or []
        if _normalize_for_match(item) in text
    ]
    keywords = [
        item for item in aspect.get("keywords") or []
        if _normalize_for_match(item) in text
    ]
    return exact, keywords


def score_run_semantic(
    case_id: str,
    summary: dict[str, Any],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score one run summary against a query-level semantic Gold asset.

    ``case_id`` is the run label; the Gold asset is selected by
    ``summary["gold_case_id"]`` when present, otherwise by ``case_id``.
    """
    asset_case_id = str(summary.get("gold_case_id") or case_id)
    asset = next((item for item in assets if item.get("case_id") == asset_case_id), None)
    if asset is None:
        raise KeyError(f"no semantic Gold asset for case: {asset_case_id}")

    negatives = [str(item) for item in asset.get("negative_semantics") or []]
    aspects = asset.get("aspects") or []
    sub_questions = _query_plan_from_trace(summary)
    primary_by_sq = _primary_by_subquestion(summary)
    records_by_id = _records_by_id(summary)
    claims = _claim_records(summary)

    retrieval_scores: list[dict[str, Any]] = []
    aspect_gaps: list[str] = []
    for aspect in aspects:
        aspect_id = str(aspect.get("aspect_id") or "")
        aligned = _align_subquestion(sub_questions, aspect)
        aligned_id = str(aligned.get("id") or "") if aligned else ""
        records = sorted(
            primary_by_sq.get(aligned_id, []),
            key=lambda item: -float(item.get("claim_fitness") or 0.0),
        )
        matched = [_match_evidence(record, aspect, negatives) for record in records]
        grades = [grade for grade, _, _, _ in matched]
        cutoff = max(1, int(aspect.get("k") or 5))
        positive_count = len([g for g in grades[:cutoff] if g >= 2])
        irrelevant = sum(1 for grade in grades[:cutoff] if grade == 0)
        positive_total = len(aspect.get("positive_semantics") or [])
        covered = {
            item
            for grade, _, pos_hits, _ in matched
            for item in pos_hits
        }
        retrieval_scores.append({
            "aspect_id": aspect_id,
            "aligned_subquestion_id": aligned_id or None,
            "retrieved_count": len(records),
            "precision_at_k": round(positive_count / cutoff, 4),
            "irrelevant_at_k": irrelevant,
            "semantic_coverage": (
                round(len(covered) / positive_total, 4) if positive_total else None
            ),
            "ndcg_at_k": _ndcg(grades, cutoff=cutoff),
            "matched_positive_semantics": sorted(covered),
        })
        if aligned is None:
            aspect_gaps.append(aspect_id)

    observations: list[dict[str, Any]] = []
    for claim in claims:
        for evidence_id in claim.get("evidence_ids") or []:
            record = records_by_id.get(str(evidence_id))
            if record is None:
                continue
            text = _evidence_text(record)
            neg_hits = [item for item in negatives if item.casefold() in text]
            observed = str((claim.get("verification_result") or {}).get("verdict") or "")
            expected = "insufficient" if neg_hits else "supports"
            observations.append({
                "claim_id": str(claim.get("claim_id") or ""),
                "evidence_id": str(evidence_id),
                "expected_verdict": expected,
                "observed_verdict": observed,
                "correct": observed == expected,
                "negative_hits": neg_hits,
            })

    expected = asset.get("answer") or {}
    expected_status = str(expected.get("run_status") or "")
    expected_confidence = str(expected.get("confidence") or "")
    expected_factcheck = str(expected.get("factcheck_status") or "")
    claim_aspect_hits: dict[str, bool] = {}
    claim_aspect_detail: dict[str, dict[str, list[str]]] = {}
    for aspect in aspects:
        aspect_id = str(aspect.get("aspect_id") or "")
        exact_hits: set[str] = set()
        keyword_hits: set[str] = set()
        for claim in claims:
            exact, keywords = _claim_aspect_hits(claim, aspect)
            exact_hits.update(exact)
            keyword_hits.update(keywords)
        claim_aspect_hits[aspect_id] = bool(exact_hits or keyword_hits)
        claim_aspect_detail[aspect_id] = {
            "exact_positive_semantics": sorted(exact_hits),
            "keywords": sorted(keyword_hits),
        }

    answer = {
        "expected_run_status": expected_status,
        "actual_run_status": str(summary.get("run_status") or ""),
        "run_status_match": (
            True if not expected_status
            else str(summary.get("run_status") or "") == expected_status
        ),
        "confidence_match": (
            True if not expected_confidence
            else str(summary.get("confidence") or "") == expected_confidence
        ),
        "factcheck_match": (
            True if not expected_factcheck
            else str(summary.get("factcheck_status") or "") == expected_factcheck
        ),
        "aspect_coverage": {
            aspect_id: covered for aspect_id, covered in claim_aspect_hits.items()
        },
        "aspect_coverage_detail": claim_aspect_detail,
        "aspect_gaps": aspect_gaps,
        "generated_claim_count": len(claims),
        "invalid_citation_count": int(summary.get("invalid_citation_count") or 0),
    }

    budget = summary.get("budget_consumed") or {}
    total_tokens = int(budget.get("input_tokens") or 0) + int(budget.get("output_tokens") or 0)
    return {
        "case_id": case_id,
        "query": str(summary.get("query") or asset.get("query") or ""),
        "retrieval": retrieval_scores,
        "verification": {
            "observed_count": len(observations),
            "verdict_accuracy": (
                round(sum(1 for item in observations if item["correct"]) / len(observations), 4)
                if observations else None
            ),
            "negative_evidence_cited_as_support": [
                item for item in observations
                if item["negative_hits"] and item["observed_verdict"] == "supports"
            ],
            "observations": observations,
        },
        "answer": answer,
        "runtime": {
            "run_status": str(summary.get("run_status") or ""),
            "confidence": str(summary.get("confidence") or ""),
            "factcheck_status": str(summary.get("factcheck_status") or ""),
            "elapsed_ms": summary.get("elapsed_ms"),
            "input_tokens": int(budget.get("input_tokens") or 0),
            "output_tokens": int(budget.get("output_tokens") or 0),
            "total_tokens": total_tokens,
            "estimated_cost_usd": summary.get("estimated_cost"),
        },
    }


def score_runs_semantic(
    run_summaries: dict[str, dict[str, Any]],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    results = [
        score_run_semantic(case_id, summary, assets)
        for case_id, summary in run_summaries.items()
    ]
    retrieval_rows = [row for item in results for row in item.get("retrieval") or []]
    answer_rows = [item.get("answer") or {} for item in results]
    runtime_rows = [item.get("runtime") or {} for item in results]
    return {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "results": results,
        "aggregate": {
            "run_count": len(results),
            "retrieval": {
                "mean_precision_at_k": _mean(row.get("precision_at_k") for row in retrieval_rows),
                "mean_irrelevant_at_k": _mean(row.get("irrelevant_at_k") for row in retrieval_rows),
                "mean_semantic_coverage": _mean(row.get("semantic_coverage") for row in retrieval_rows),
                "mean_ndcg_at_k": _mean(row.get("ndcg_at_k") for row in retrieval_rows),
                "unmatched_aspect_count": sum(
                    1 for item in results for row in item.get("retrieval") or []
                    if row.get("aligned_subquestion_id") is None
                ),
            },
            "verification": {
                "mean_verdict_accuracy": _mean(
                    item.get("verification", {}).get("verdict_accuracy") for item in results
                ),
                "negative_evidence_cited_as_support_count": sum(
                    len(item.get("verification", {}).get("negative_evidence_cited_as_support") or [])
                    for item in results
                ),
            },
            "answer": {
                "run_status_match_count": sum(
                    1 for row in answer_rows if row.get("run_status_match")
                ),
                "confidence_match_count": sum(1 for row in answer_rows if row.get("confidence_match")),
                "factcheck_match_count": sum(1 for row in answer_rows if row.get("factcheck_match")),
            },
            "runtime": {
                "p95_latency_ms": _p95(row.get("elapsed_ms") for row in runtime_rows),
                "mean_latency_ms": _mean(row.get("elapsed_ms") for row in runtime_rows),
                "mean_total_tokens": _mean(row.get("total_tokens") for row in runtime_rows),
                "cost_available": all(
                    row.get("estimated_cost_usd") is not None for row in runtime_rows
                ),
            },
        },
    }
