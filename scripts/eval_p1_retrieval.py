"""Evaluate P1 full-text retrieval before and after semantic reranking."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

PAPERS = {
    "2305.06453v4": ("Autonomous GIS", ROOT / "tmp/pdfs/2305.06453v4.pdf"),
    "2407.21024v2": ("LLM-Find", ROOT / "tmp/pdfs/2407.21024v2.pdf"),
    "2410.12376v2": ("ShapefileGPT", ROOT / "data/documents/papers/pdfs/2410.12376v2.pdf"),
}


def load_labels(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"retrieval labels must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def build_documents() -> list[Any]:
    from conflux.knowledge.paper_indexer import _full_text_documents
    from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord
    from conflux.paper_ingestion.pdf_text import extract_pdf_text

    documents = []
    for paper_id, (title, path) in PAPERS.items():
        if not path.exists():
            raise FileNotFoundError(path)
        paper = PaperRecord(id=paper_id, title=title, abstract="P1 retrieval fixture", pdf_url=path.as_uri())
        analysis = PaperAnalysis(paper_id=paper_id, relevance_score=0.99, reading_level="deep")
        decision = decide_ingestion(paper, analysis, policy=default_policy(allow_full_text=True))
        extraction = extract_pdf_text(path)
        if not extraction.text.strip():
            raise RuntimeError(f"PDF extraction failed for {paper_id}: {extraction.status}")
        documents.extend(_full_text_documents(paper, analysis, decision, extraction.text))
    return documents


def offline_rank(query: str, documents: list[Any], k: int) -> list[Any]:
    from conflux.query_planner import important_terms, plan_queries

    plan = plan_queries(query, target="rag")
    terms = important_terms(" ".join(plan.subqueries))
    ranked = []
    for document in documents:
        text = (document.page_content or "").casefold()
        matched = sum(term.casefold() in text for term in terms)
        score = matched / max(1, len(terms))
        section = str((document.metadata or {}).get("paper_section") or "")
        if any(marker in query.casefold() for marker in ("局限", "限制", "未来", "幻觉", "成本")) and section in {"limitations", "future_work"}:
            score += 0.2
        ranked.append((score, document))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:k]]


def real_rank(query: str, retriever: Any, reranker: Any, k: int) -> tuple[list[Any], list[Any]]:
    from conflux.query_planner import plan_queries

    candidates: dict[str, Any] = {}
    scores: dict[str, float] = {}
    for subquery in plan_queries(query, target="rag").subqueries:
        for document in retriever.search(subquery):
            key = str((document.metadata or {}).get("chunk_id") or document.page_content[:120])
            score = float((document.metadata or {}).get("rrf_score") or 0.0)
            if key not in candidates or score > scores[key]:
                candidates[key] = document
                scores[key] = score
    baseline = [candidates[key] for key in sorted(candidates, key=scores.get, reverse=True)[: max(k, 16)]]
    scored = [
        {
            "doc": document,
            "score": float((document.metadata or {}).get("rrf_score") or 0.0),
            "breakdown": {
                "dense_score": (document.metadata or {}).get("dense_score"),
                "bm25_score": (document.metadata or {}).get("bm25_score"),
                "rrf_score": (document.metadata or {}).get("rrf_score"),
            },
        }
        for document in baseline
    ]
    reranked = reranker.rerank(query, scored, limit=k)
    return baseline[:k], [item["doc"] for item in reranked[:k]]


def evaluate_ranking(labels: list[dict[str, Any]], rankings: dict[str, list[Any]], k: int) -> dict[str, Any]:
    cases = []
    recalls = []
    ndcgs = []
    section_hits = []
    irrelevant = []
    for label in labels:
        docs = rankings.get(str(label["id"])) or []
        grades = [_grade(document, label) for document in docs[:k]]
        recall = 1.0 if any(grade >= 2 for grade in grades) else 0.0
        ndcg = _ndcg(grades, k)
        section_hit = 1.0 if any(_section_match(document, label) for document in docs[:k]) else 0.0
        irrelevant_rate = sum(grade == 0 for grade in grades) / len(grades) if grades else 1.0
        recalls.append(recall)
        ndcgs.append(ndcg)
        section_hits.append(section_hit)
        irrelevant.append(irrelevant_rate)
        cases.append({
            "id": label["id"],
            "query": label["query"],
            "recall": recall,
            "ndcg": round(ndcg, 4),
            "section_hit": section_hit,
            "irrelevant_rate": round(irrelevant_rate, 4),
            "top": [_document_row(document, grade) for document, grade in zip(docs[:k], grades)],
        })
    return {
        "metrics": {
            f"recall_at_{k}": round(statistics.mean(recalls), 4) if recalls else 0.0,
            f"ndcg_at_{k}": round(statistics.mean(ndcgs), 4) if ndcgs else 0.0,
            "section_hit_rate": round(statistics.mean(section_hits), 4) if section_hits else 0.0,
            "irrelevant_hit_rate": round(statistics.mean(irrelevant), 4) if irrelevant else 1.0,
            "case_count": len(labels),
        },
        "cases": cases,
    }


def _grade(document: Any, label: dict[str, Any]) -> int:
    metadata = document.metadata or {}
    if str(metadata.get("paper_id") or "") != str(label.get("paper_id") or ""):
        return 0
    if _page_match(document, label) and _section_match(document, label):
        return 3
    if _page_match(document, label) or _section_match(document, label):
        return 2
    return 1


def _page_match(document: Any, label: dict[str, Any]) -> bool:
    metadata = document.metadata or {}
    expected_start, expected_end = [int(value) for value in label.get("pages") or (0, 0)]
    actual_start = int(metadata.get("page_start") or 0)
    actual_end = int(metadata.get("page_end") or actual_start)
    return actual_start <= expected_end and actual_end >= expected_start


def _section_match(document: Any, label: dict[str, Any]) -> bool:
    expected = str(label.get("section") or "").casefold()
    actual = str((document.metadata or {}).get("paper_section") or "").casefold()
    if expected == "discussion":
        return actual in {"discussion", "limitations", "future_work"}
    if expected == "method":
        return actual in {"method", "methods", "methodology"}
    if expected == "results":
        return actual in {"results", "discussion", "limitations"}
    return actual == expected


def _ndcg(grades: list[int], k: int) -> float:
    dcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades[:k]))
    ideal_grades = sorted([*grades, 3], reverse=True)[:k]
    ideal = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal_grades))
    return dcg / ideal if ideal else 0.0


def _document_row(document: Any, grade: int) -> dict[str, Any]:
    metadata = document.metadata or {}
    return {
        "paper_id": metadata.get("paper_id"),
        "section": metadata.get("paper_section"),
        "page_start": metadata.get("page_start"),
        "page_end": metadata.get("page_end"),
        "chunk_id": metadata.get("chunk_id"),
        "grade": grade,
        "excerpt": str(document.page_content or "")[:240].replace("\n", " "),
    }


def write_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "p1_retrieval_eval.json"
    md_path = out_dir / "p1_retrieval_eval.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# P1 RAG 检索评测", ""]
    for name in ("baseline", "semantic_rerank"):
        result = payload.get(name)
        if not result:
            continue
        metrics = result["metrics"]
        lines.extend([
            f"## {name}",
            "",
            *[f"- {key}: {value}" for key, value in metrics.items()],
            "",
            "| Case | Recall | NDCG | Section | Irrelevant | Top chunk |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for case in result["cases"]:
            top = case["top"][0] if case["top"] else {}
            lines.append(
                f"| {case['id']} | {case['recall']} | {case['ndcg']} | {case['section_hit']} | "
                f"{case['irrelevant_rate']} | {top.get('chunk_id', '')} |"
            )
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate P1 full-text RAG retrieval.")
    parser.add_argument("--labels", default="data/p1_retrieval_eval.yaml")
    parser.add_argument("--out-dir", default="reports/eval/p1")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--real", action="store_true", help="Use configured embeddings and semantic reranker")
    parser.add_argument("--depth", choices=("quick", "standard", "deep"), default="standard")
    args = parser.parse_args()

    labels = load_labels(ROOT / args.labels)
    documents = build_documents()
    baseline_rankings = {str(item["id"]): offline_rank(str(item["query"]), documents, args.k) for item in labels}
    payload: dict[str, Any] = {
        "real_api": bool(args.real),
        "document_count": len(documents),
        "baseline": evaluate_ranking(labels, baseline_rankings, args.k),
    }
    if args.real:
        load_dotenv(ROOT / ".env", override=False)
        load_dotenv(ROOT / ".env.workbench", override=False)
        os.environ["CONFLUX_RETRIEVAL__TOP_K"] = str(max(args.k * 2, 20))
        os.environ["CONFLUX_RETRIEVAL__FINAL_K"] = str(args.k)
        from conflux import config
        from conflux.model_factory import create_embedding_model, create_research_models
        from conflux.rag.indexer import index_documents
        from conflux.rag.reranker import SemanticReranker
        from conflux.rag.retriever import HybridRetriever
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from langchain_chroma import Chroma

        config._config = None
        store = Chroma(
            client=chromadb.Client(settings=ChromaSettings(anonymized_telemetry=False)),
            collection_name=f"p1_eval_{int(time.time())}",
            embedding_function=create_embedding_model(),
        )
        index_documents(store, documents)
        models, model_trace = create_research_models(args.depth)
        retriever = HybridRetriever(store)
        reranker = SemanticReranker(models["reranker"])
        dense_rankings: dict[str, list[Any]] = {}
        semantic_rankings: dict[str, list[Any]] = {}
        for item in labels:
            before, after = real_rank(str(item["query"]), retriever, reranker, args.k)
            dense_rankings[str(item["id"])] = before
            semantic_rankings[str(item["id"])] = after
        payload["dense_hybrid"] = evaluate_ranking(labels, dense_rankings, args.k)
        payload["semantic_rerank"] = evaluate_ranking(labels, semantic_rankings, args.k)
        payload["model_trace"] = model_trace
    md_path, json_path = write_outputs(payload, ROOT / args.out_dir)
    print(f"P1 retrieval Markdown: {md_path}")
    print(f"P1 retrieval JSON: {json_path}")
    print(json.dumps({key: value["metrics"] for key, value in payload.items() if isinstance(value, dict) and "metrics" in value}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
