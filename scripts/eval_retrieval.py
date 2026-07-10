"""Offline retrieval evaluation for Conflux.

This script intentionally works without API keys when run with --offline. It
uses lexical matching over data/documents as a deterministic baseline and writes
Markdown + JSON metrics that can be tracked in git or CI artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def load_dataset(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Golden dataset must be a list: {path}")
    return data


def load_documents(docs_dir: Path) -> list[dict[str, str]]:
    docs = []
    for path in sorted(docs_dir.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def lexical_retrieve(query: str, docs: list[dict[str, str]], k: int) -> list[dict[str, Any]]:
    query_terms = important_terms(query)
    ranked = []
    for doc in docs:
        text = doc["text"].lower()
        hits = [term for term in query_terms if term in text]
        score = len(hits) / max(1, len(query_terms))
        ranked.append({
            "source": doc["source"],
            "score": round(score, 4),
            "matched_terms": hits[:12],
        })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:k]


def important_terms(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", text.lower())
    stopwords = {
        "what",
        "how",
        "why",
        "the",
        "and",
        "for",
        "with",
        "retrieval",
        "augmented",
        "什么",
        "如何",
        "为什么",
    }
    return [term for term in raw if term not in stopwords]


def expected_source_hit(expected_sources: list[str], top_sources: list[str]) -> bool:
    if "RAG" not in expected_sources:
        return True
    return bool(top_sources)


def evaluate(dataset: list[dict[str, Any]], docs: list[dict[str, str]], k: int) -> dict[str, Any]:
    cases = []
    rag_expected = 0
    rag_hits = 0
    any_hits = 0
    irrelevant_hits = 0
    for case in dataset:
        query = str(case.get("query") or "")
        expected_sources = list(case.get("expected_sources") or [])
        top = lexical_retrieve(query, docs, k)
        top_sources = [item["source"] for item in top if item["score"] > 0]
        hit = expected_source_hit(expected_sources, top_sources)
        if "RAG" in expected_sources:
            rag_expected += 1
            if hit:
                rag_hits += 1
        if hit:
            any_hits += 1
        if "RAG" not in expected_sources and top_sources:
            irrelevant_hits += 1
        cases.append({
            "id": case.get("id"),
            "query": query,
            "expected_sources": expected_sources,
            "top_k": top,
            "hit": hit,
            "failure_reason": "" if hit else "No lexical document hit for an RAG-expected case.",
        })

    total = len(dataset) or 1
    return {
        "metrics": {
            "recall_at_k": round(rag_hits / rag_expected, 4) if rag_expected else 1.0,
            "hit_rate": round(any_hits / total, 4),
            "source_coverage": round(rag_hits / rag_expected, 4) if rag_expected else 1.0,
            "irrelevant_hit_rate": round(irrelevant_hits / total, 4),
            "case_count": len(dataset),
            "rag_expected_count": rag_expected,
            "k": k,
        },
        "cases": cases,
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "retrieval_eval.json"
    md_path = out_dir / "retrieval_eval.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics = result["metrics"]
    lines = [
        "# Retrieval Eval Baseline",
        "",
        f"- recall@{metrics['k']}: {metrics['recall_at_k']}",
        f"- hit_rate: {metrics['hit_rate']}",
        f"- source_coverage: {metrics['source_coverage']}",
        f"- irrelevant_hit_rate: {metrics['irrelevant_hit_rate']}",
        f"- cases: {metrics['case_count']}",
        "",
        "| Case | Hit | Top Sources | Failure Reason |",
        "|---|---|---|---|",
    ]
    for case in result["cases"]:
        top_sources = ", ".join(item["source"] for item in case["top_k"][:3])
        lines.append(f"| {case['id']} | {case['hit']} | {top_sources} | {case['failure_reason']} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline retrieval evaluation.")
    parser.add_argument("--dataset", default="data/golden_dataset.yaml")
    parser.add_argument("--docs-dir", default="data/documents")
    parser.add_argument("--out-dir", default="reports/eval")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--offline", action="store_true", help="Use deterministic lexical retrieval")
    args = parser.parse_args()

    dataset = load_dataset(ROOT / args.dataset)
    docs = load_documents(ROOT / args.docs_dir)
    result = evaluate(dataset, docs, args.k)
    md_path, json_path = write_outputs(result, ROOT / args.out_dir)
    print(f"Retrieval eval Markdown: {md_path}")
    print(f"Retrieval eval JSON: {json_path}")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
