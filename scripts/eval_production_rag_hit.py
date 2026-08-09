"""生产级 RAG 命中率评测兜底。

用 data/rag_eval 三语评测集直接跑当前 HybridRetriever（生产检索参数），
统计相关来源是否进入 top-k；支持 --top-k/--final-k 覆盖参数，用于对比
旧配置（top_k=10/final_k=5）与新配置（top_k=60/final_k=10）。

用法:
    python scripts/eval_production_rag_hit.py
    python scripts/eval_production_rag_hit.py --top-k 10 --final-k 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_queries() -> list[dict]:
    rows: list[dict] = []
    for name in ("zh_zh", "zh_en", "en_en"):
        path = PROJECT_ROOT / "data" / "rag_eval" / f"{name}.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for item in payload:
            rows.append({
                "id": f"{name}:{item.get('id')}",
                "query": str(item.get("query") or ""),
                "relevant_sources": [str(s) for s in item.get("relevant_sources") or []],
                "language": name,
            })
    return rows


def _matches(source: str, relevant: str) -> bool:
    source_name = Path(str(source).replace("\\", "/")).name
    if source_name == relevant:
        return True
    # R1 en-en 标签用 PDF 文件名（如 2410.12376v2.pdf），索引 source 是
    # paper-{arxiv_id}#summary.md；按论文 ID 匹配，而不是整文件名。
    relevant_id = Path(relevant).stem
    if "paper-" in source_name and relevant_id and relevant_id in source_name:
        return True
    return False


def _hit_at_k(docs: list, relevant_sources: list[str]) -> dict:
    hit = False
    hit_rank = None
    for rank, doc in enumerate(docs, 1):
        source = str(doc.metadata.get("source") or "")
        if any(_matches(source, item) for item in relevant_sources):
            hit = True
            hit_rank = rank
            break
    return {"hit": hit, "first_hit_rank": hit_rank}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate production RAG hit rate")
    parser.add_argument("--top-k", type=int, default=None, help="override retrieval.top_k")
    parser.add_argument("--final-k", type=int, default=None, help="override retrieval.final_k")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "eval" / "rag_hit" / "hit_report.json"))
    args = parser.parse_args()

    from conflux import config as cfg
    from conflux.rag import create_vector_store, HybridRetriever

    raw = cfg.load()
    original_top_k = raw["retrieval"]["top_k"]
    original_final_k = raw["retrieval"]["final_k"]
    if args.top_k is not None:
        raw["retrieval"]["top_k"] = args.top_k
    if args.final_k is not None:
        raw["retrieval"]["final_k"] = args.final_k

    retriever = HybridRetriever(create_vector_store())
    rows = _load_queries()
    results = []
    for item in rows:
        docs = retriever.search(item["query"])
        hit = _hit_at_k(docs, item["relevant_sources"])
        results.append({**item, "returned": len(docs), **hit})

    by_language: dict[str, dict] = {}
    for language in ("zh_zh", "zh_en", "en_en"):
        group = [r for r in results if r["language"] == language]
        hits = [r for r in group if r["hit"]]
        by_language[language] = {
            "query_count": len(group),
            "hit_count": len(hits),
            "hit_rate": round(len(hits) / len(group), 4) if group else None,
            "mean_first_hit_rank": (
                round(sum(r["first_hit_rank"] for r in hits) / len(hits), 2) if hits else None
            ),
        }
    aggregate = {
        "top_k": raw["retrieval"]["top_k"],
        "final_k": raw["retrieval"]["final_k"],
        "query_count": len(results),
        "hit_count": sum(1 for r in results if r["hit"]),
        "hit_rate": round(sum(1 for r in results if r["hit"]) / len(results), 4),
        "by_language": by_language,
    }
    payload = {"config": aggregate, "results": results}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    print(f"wrote: {output}")

    raw["retrieval"]["top_k"] = original_top_k
    raw["retrieval"]["final_k"] = original_final_k
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
