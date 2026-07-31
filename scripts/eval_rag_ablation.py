"""RAG retrieval ablation matrix — 5 configs × N languages.

Compares keyword, dense-only, hybrid, hybrid+rerank, and cross-lingual
retrieval pipelines across language scenarios.

Outputs: reports/eval/rag_ablation/rag_ablation.md + rag_ablation.json
"""

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

# ── Shared definitions ──────────────────────────────────────────────


def load_labels(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"retrieval labels must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def _grade_keyword(document: Any, label: dict[str, Any]) -> int:
    """Grade by keyword overlap with ground-truth doc source match."""
    metadata = document.metadata or {}
    doc_source = str(metadata.get("source") or metadata.get("file") or "")
    expected_source = str(label.get("doc_source") or "")
    expected_kw = [kw.casefold() for kw in label.get("expected_keywords") or []]
    content = str(document.page_content or "").casefold()

    if doc_source != expected_source:
        return 0  # wrong document
    if not expected_kw:
        return 1  # correct doc, no keyword check
    matched = sum(kw in content for kw in expected_kw)
    if matched >= len(expected_kw):
        return 3
    if matched >= len(expected_kw) * 0.5:
        return 2
    return 1


def _grade_paper(document: Any, label: dict[str, Any]) -> int:
    """Grade by paper_id + page + section overlap."""
    metadata = document.metadata or {}
    if str(metadata.get("paper_id") or "") != str(label.get("paper_id") or ""):
        return 0
    # page match
    expected_start, expected_end = [int(v) for v in label.get("pages") or (0, 0)]
    actual_start = int(metadata.get("page_start") or 0)
    actual_end = int(metadata.get("page_end") or actual_start)
    page_ok = actual_start <= expected_end and actual_end >= expected_start
    # section match
    expected_sec = str(label.get("section") or "").casefold()
    actual_sec = str(metadata.get("paper_section") or "").casefold()
    section_ok = False
    if expected_sec == "discussion":
        section_ok = actual_sec in {"discussion", "limitations", "future_work"}
    elif expected_sec == "method":
        section_ok = actual_sec in {"method", "methods", "methodology"}
    elif expected_sec == "results":
        section_ok = actual_sec in {"results", "discussion", "limitations"}
    else:
        section_ok = actual_sec == expected_sec
    if page_ok and section_ok:
        return 3
    if page_ok or section_ok:
        return 2
    return 1


def _ndcg(grades: list[int], k: int) -> float:
    dcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades[:k]))
    ideal_grades = sorted([*grades, 3], reverse=True)[:k]
    ideal = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal_grades))
    return dcg / ideal if ideal else 0.0


def offline_rank(query: str, documents: list[Any], k: int) -> list[Any]:
    """Simple term-frequency keyword rank — no API needed."""
    q_lower = query.casefold()
    ranked = []
    for document in documents:
        text = (document.page_content or "").casefold()
        source = str((document.metadata or {}).get("source") or "")
        score = sum(1 for c in q_lower if c in text) / max(1, len(q_lower))
        # Bonus for source name match
        if source.casefold() in q_lower or any(w in source.casefold() for w in q_lower.split()):
            score += 0.3
        ranked.append((score, document))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:k]]


def _load_documents_from_dir(doc_dir: Path) -> list[Any]:
    """Load .md and .txt files from a directory as LangChain Documents."""
    from langchain_core.documents import Document

    docs: list[Document] = []
    for path in sorted(doc_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".md", ".txt"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue
        source = path.relative_to(doc_dir).as_posix()
        docs.append(Document(page_content=text, metadata={"source": source, "file": source}))
    return docs


def real_rank(query: str, retriever: Any, reranker: Any | None, k: int) -> tuple[list[Any], list[Any] | None]:
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
    baseline = [candidates[key] for key in sorted(candidates, key=scores.get, reverse=True)[:max(k, 16)]]
    if reranker is None:
        return baseline[:k], None
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
    baseline = [candidates[key] for key in sorted(candidates, key=scores.get, reverse=True)[:max(k, 16)]]
    if reranker is None:
        return baseline[:k], None
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

# ============================================================
# Retrieval configurations
# ============================================================

RetrievalConfig = dict[str, Any]

FIVE_CONFIGS: dict[str, RetrievalConfig] = {
    "keyword": {
        "label": "Keyword (offline)",
        "description": "Exact term match + heuristic section bonus.",
        "offline": True,
    },
    "dense_only": {
        "label": "Dense only",
        "description": "Pure vector similarity, BM25 disabled.",
        "offline": False,
        "env": {
            "CONFLUX_RETRIEVAL__DENSE_WEIGHT": "1.0",
            "CONFLUX_RETRIEVAL__BM25_WEIGHT": "0.0",
        },
        "rerank": False,
    },
    "hybrid": {
        "label": "Hybrid (Dense+BM25)",
        "description": "Dense 0.7 + BM25 0.3, RRF fusion.",
        "offline": False,
        "env": {
            "CONFLUX_RETRIEVAL__DENSE_WEIGHT": "0.7",
            "CONFLUX_RETRIEVAL__BM25_WEIGHT": "0.3",
        },
        "rerank": False,
    },
    "hybrid_rerank": {
        "label": "Hybrid + Rerank",
        "description": "Hybrid retrieval followed by LLM semantic reranking.",
        "offline": False,
        "env": {
            "CONFLUX_RETRIEVAL__DENSE_WEIGHT": "0.7",
            "CONFLUX_RETRIEVAL__BM25_WEIGHT": "0.3",
        },
        "rerank": True,
    },
    "cross_lingual": {
        "label": "Cross-lingual (dense≥0.9)",
        "description": "Dense-heavy config for cross-language retrieval.",
        "offline": False,
        "env": {
            "CONFLUX_RETRIEVAL__DENSE_WEIGHT": "0.9",
            "CONFLUX_RETRIEVAL__BM25_WEIGHT": "0.1",
        },
        "rerank": True,
    },
}

# ============================================================
# Language scenarios
# ============================================================

LanguageScenario = dict[str, Any]

LANG_SCENARIOS: dict[str, LanguageScenario] = {
    "zh-zh": {
        "label": "zh query → zh documents",
        "description": "Chinese queries against Chinese GIS markdown docs.",
        "labels_file": "data/p1_retrieval_eval_zh.yaml",
        "doc_dir": "data/documents",
        "grading": "keyword",  # keyword-based grading for markdown docs
    },
    # Paper-based scenarios (require PDFs in tmp/pdfs/):
    # "zh-en": { ... "labels_file": "data/p1_retrieval_eval.yaml", "grading": "paper" },
    # "en-en": { ... "labels_file": "data/p1_retrieval_eval_en.yaml", "grading": "paper" },
}


# ============================================================
# Full evaluation (includes MRR)
# ============================================================

def evaluate_ranking_full(
    labels: list[dict[str, Any]], rankings: dict[str, list[Any]], k: int,
    grade_fn: Any = _grade_keyword,
) -> dict[str, Any]:
    """Compute recall@k, ndcg@5/10, section_hit_rate, irrelevant_hit_rate, MRR."""
    cases = []
    recalls = []
    ndcgs_5 = []
    ndcgs_10 = []
    section_hits = []
    irrelevant = []
    mrrs = []

    for label in labels:
        docs = rankings.get(str(label["id"])) or []
        grades = [grade_fn(document, label) for document in docs[:k]]
        recall = 1.0 if any(grade >= 2 for grade in grades) else 0.0
        ndcg_5 = _ndcg(grades, 5)
        ndcg_10 = _ndcg(grades, k)
        section_hit = 1.0 if any(grade >= 3 for grade in grades) else 0.0  # grade 3 = perfect match
        irrelevant_rate = sum(grade == 0 for grade in grades) / len(grades) if grades else 1.0
        # MRR: first relevant doc (grade ≥ 2)
        first_rel = next((i + 1 for i, g in enumerate(grades) if g >= 2), 0)
        mrr = 1.0 / first_rel if first_rel else 0.0

        recalls.append(recall)
        ndcgs_5.append(ndcg_5)
        ndcgs_10.append(ndcg_10)
        section_hits.append(section_hit)
        irrelevant.append(irrelevant_rate)
        mrrs.append(mrr)

        cases.append({
            "id": label["id"],
            "query": label["query"],
            "recall": recall,
            "ndcg": round(ndcg_10, 4),
            "ndcg_5": round(ndcg_5, 4),
            "section_hit": section_hit,
            "irrelevant_rate": round(irrelevant_rate, 4),
            "mrr": round(mrr, 4),
        })

    return {
        "metrics": {
            f"recall_at_{k}": round(statistics.mean(recalls), 4) if recalls else 0.0,
            "ndcg_at_5": round(statistics.mean(ndcgs_5), 4) if ndcgs_5 else 0.0,
            "ndcg_at_10": round(statistics.mean(ndcgs_10), 4) if ndcgs_10 else 0.0,
            "mrr": round(statistics.mean(mrrs), 4) if mrrs else 0.0,
            "section_hit_rate": round(statistics.mean(section_hits), 4) if section_hits else 0.0,
            "irrelevant_hit_rate": round(statistics.mean(irrelevant), 4) if irrelevant else 1.0,
            "case_count": len(labels),
        },
        "cases": cases,
    }


# ============================================================
# One config run
# ============================================================

def run_one_config(
    cfg: RetrievalConfig,
    labels: list[dict[str, Any]],
    documents: list[Any],
    k: int,
    store_factory,
    embedding_model,
    models: dict[str, Any],
    grade_fn: Any = _grade_keyword,
) -> dict[str, Any]:
    """Run retrieval evaluation for a single configuration."""
    if cfg.get("offline"):
        rankings = {str(item["id"]): offline_rank(str(item["query"]), documents, k) for item in labels}
        return evaluate_ranking_full(labels, rankings, k, grade_fn=grade_fn)

    # Apply env overrides for this config
    for key, value in cfg.get("env", {}).items():
        os.environ[key] = value

    from conflux.rag.indexer import index_documents
    from conflux.rag.reranker import SemanticReranker
    from conflux.rag.retriever import HybridRetriever

    store = store_factory()
    index_documents(store, documents)
    retriever = HybridRetriever(store)
    reranker = SemanticReranker(models["reranker"]) if cfg.get("rerank") else None

    rankings: dict[str, list[Any]] = {}
    for item in labels:
        query = str(item["query"])
        if reranker:
            before, after = real_rank(query, retriever, reranker, k)
            rankings[str(item["id"])] = after
        else:
            # Run retriever directly without reranker
            docs = retriever.search(query)[:k]
            rankings[str(item["id"])] = docs

    result = evaluate_ranking_full(labels, rankings, k, grade_fn=grade_fn)
    return result


# ============================================================
# Matrix builder
# ============================================================

def build_ablation_matrix(
    configs: dict[str, RetrievalConfig],
    languages: dict[str, LanguageScenario],
    k: int,
    store_factory,
    embedding_model,
    models: dict[str, Any],
) -> dict[str, Any]:
    """Run all (config × language) combinations and return comparison matrix."""

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    summaries: dict[str, dict[str, dict[str, float]]] = {}

    for lang_key, lang_info in languages.items():
        matrix[lang_key] = {}
        summaries[lang_key] = {}
        labels_path = ROOT / lang_info["labels_file"]
        labels = load_labels(labels_path)

        # Select grading function
        grading = lang_info.get("grading", "keyword")
        grade_fn = _grade_keyword if grading == "keyword" else _grade_paper

        # Load documents
        doc_dir = lang_info.get("doc_dir")
        if doc_dir:
            all_docs = _load_documents_from_dir(ROOT / doc_dir)
        else:
            all_docs = _load_documents_from_dir(ROOT / "data/documents")
        print(f"  [{lang_key}] {len(labels)} labels, {len(all_docs)} docs")

        for cfg_key, cfg in configs.items():
            print(f"  [{lang_key}] {cfg['label']} ... ", end="", flush=True)
            t0 = time.time()
            result = run_one_config(cfg, labels, all_docs, k, store_factory, embedding_model, models, grade_fn=grade_fn)
            elapsed = time.time() - t0
            print(f"{elapsed:.1f}s  recall@{k}={result['metrics'].get(f'recall_at_{k}', '-')}  mrr={result['metrics'].get('mrr', '-')}")

            matrix[lang_key][cfg_key] = result
            summaries[lang_key][cfg_key] = {
                f"recall_at_{k}": result["metrics"].get(f"recall_at_{k}"),
                "ndcg_at_5": result["metrics"].get("ndcg_at_5"),
                "ndcg_at_10": result["metrics"].get("ndcg_at_10"),
                "mrr": result["metrics"].get("mrr"),
                "section_hit_rate": result["metrics"].get("section_hit_rate"),
                "irrelevant_hit_rate": result["metrics"].get("irrelevant_hit_rate"),
            }

    return {
        "configs": {key: cfg["label"] for key, cfg in configs.items()},
        "languages": {key: lang_info["label"] for key, lang_info in languages.items()},
        "k": k,
        "matrix": matrix,
        "summaries": summaries,
    }


# ============================================================
# Output writers
# ============================================================

def write_ablation_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "rag_ablation.json"
    md_path = out_dir / "rag_ablation.md"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    k = payload["k"]
    lines = [
        "# RAG Retrieval Ablation Matrix",
        "",
        f"**K**: {k}",
        "",
    ]

    for lang_key, summaries in payload["summaries"].items():
        lang_label = payload["languages"][lang_key]
        lines.extend([f"## {lang_label}", ""])

        # Header row
        header = ["Metric"] + [payload["configs"].get(c, c) for c in summaries]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))

        # Metric rows
        for metric in [f"recall_at_{k}", "ndcg_at_5", "ndcg_at_10", "mrr", "section_hit_rate", "irrelevant_hit_rate"]:
            row = [metric]
            for cfg_key in summaries:
                val = summaries[cfg_key].get(metric)
                if val is None:
                    row.append("—")
                elif metric == "irrelevant_hit_rate":
                    row.append(f"{val:.4f}")  # lower is better
                else:
                    row.append(f"{val:.4f}")  # higher is better
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

        # Per-case detail tables
        lines.append("### Per-case detail")
        lines.append("")
        for cfg_key in summaries:
            cfg_label = payload["configs"].get(cfg_key, cfg_key)
            lines.append(f"**{cfg_label}**")
            lines.append("")
            lines.append("| Case | Recall | NDCG | Section | Irrelevant | MRR |")
            lines.append("|---|---:|---:|---:|---:|---:|")
            cfg_cases = payload["matrix"][lang_key][cfg_key].get("cases") or []
            for case in cfg_cases:
                lines.append(
                    f"| {case['id']} | {case['recall']} | {case['ndcg']} | "
                    f"{case['section_hit']} | {case['irrelevant_rate']} | — |"
                )
            lines.append("")

    # Cross-language comparison
    if len(payload["languages"]) > 1:
        lines.extend([
            "## Cross-language Comparison",
            "",
            "Primary metric: MRR drop across languages.",
            "",
            "| Config | Metric | " + " | ".join(f"{payload['languages'][lk]}" for lk in payload["languages"]) + " |",
            "|---|---|" + "---|" * len(payload["languages"]),
        ])
        for metric in ["mrr", f"recall_at_{k}", "ndcg_at_5"]:
            for cfg_key in payload["configs"]:
                row = [payload["configs"][cfg_key], metric]
                for lk in payload["languages"]:
                    val = payload["summaries"][lk][cfg_key].get(metric)
                    row.append(f"{val:.4f}" if val else "—")
                lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


# ============================================================
# CLI
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="RAG retrieval ablation matrix.")
    parser.add_argument("--out-dir", default="reports/eval/rag_ablation")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--depth", choices=("quick", "standard", "deep"), default="standard")
    parser.add_argument("--configs", nargs="*", default=list(FIVE_CONFIGS.keys()),
                        help=f"Configs to run (default: all 5). Choices: {list(FIVE_CONFIGS.keys())}")
    parser.add_argument("--languages", nargs="*", default=list(LANG_SCENARIOS.keys()),
                        help=f"Languages to run (default: all). Choices: {list(LANG_SCENARIOS.keys())}")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.workbench", override=False)

    # Select configs and languages
    selected_configs = {key: FIVE_CONFIGS[key] for key in args.configs if key in FIVE_CONFIGS}
    selected_langs = {key: LANG_SCENARIOS[key] for key in args.languages if key in LANG_SCENARIOS}

    if not selected_configs:
        print("No valid configs selected.")
        return 1
    if not selected_langs:
        print("No valid languages selected.")
        return 1

    # Set up API backends
    os.environ["CONFLUX_RETRIEVAL__TOP_K"] = str(max(args.k * 2, 20))
    os.environ["CONFLUX_RETRIEVAL__FINAL_K"] = str(args.k)

    from conflux import config
    from conflux.model_factory import create_embedding_model, create_research_models
    from conflux.rag.indexer import index_documents
    from conflux.rag.retriever import HybridRetriever
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from langchain_chroma import Chroma

    # Reset config so env overrides take effect per-config
    config._config = None
    embedding_model = create_embedding_model()
    models, model_trace = create_research_models(args.depth)

    # Store factory: creates a fresh in-memory Chroma collection for each config
    store_counter = 0

    def store_factory():
        nonlocal store_counter
        store_counter += 1
        return Chroma(
            client=chromadb.Client(settings=ChromaSettings(anonymized_telemetry=False)),
            collection_name=f"r1_ablation_{int(time.time())}_{store_counter}",
            embedding_function=embedding_model,
        )

    print(f"RAG ablation: {len(selected_configs)} configs × {len(selected_langs)} languages = {len(selected_configs)*len(selected_langs)} runs")
    print(f"Depth: {args.depth}  k: {args.k}")
    print(f"Models: {model_trace}")
    print()

    payload = build_ablation_matrix(
        selected_configs, selected_langs, args.k,
        store_factory, embedding_model, models,
    )
    payload["model_trace"] = model_trace

    md_path, json_path = write_ablation_outputs(payload, ROOT / args.out_dir)
    print(f"\nMarkdown: {md_path}")
    print(f"JSON: {json_path}")

    # Quick summary
    for lang_key, summaries in payload["summaries"].items():
        print(f"\n--- {payload['languages'][lang_key]} ---")
        header = f"{'Config':<20} {'recall@{:d}':>10} {'NDCG@5':>8} {'NDCG@10':>8} {'MRR':>8} {'Section':>8} {'Irrel':>8}".format(args.k)
        print(header)
        print("-" * len(header))
        for cfg_key, metrics in summaries.items():
            print(
                f"{payload['configs'][cfg_key]:<20} "
                f"{metrics.get(f'recall_at_{args.k}', 0) or 0:>10.4f} "
                f"{metrics.get('ndcg_at_5', 0) or 0:>8.4f} "
                f"{metrics.get('ndcg_at_10', 0) or 0:>8.4f} "
                f"{metrics.get('mrr', 0) or 0:>8.4f} "
                f"{metrics.get('section_hit_rate', 0) or 0:>8.4f} "
                f"{metrics.get('irrelevant_hit_rate', 0) or 0:>8.4f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
