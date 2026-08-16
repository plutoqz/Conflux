"""RAG 扩展评测 —— 在 30 题三语生产集上补充 Recall@k / MRR / nDCG@10。

复用 data/rag_eval 三语集与 HybridRetriever（生产参数），对每个 query 取
final_k=20 的有序结果，记录每个 relevant source 的首次命中 rank，再计算：

- Recall@1/3/5/10/20（单相关源时等价于 hit@k）
- MRR（首个相关源的倒数排名均值）
- nDCG@10（二值相关性：命中 rank r<=10 得 1/log2(r+1)，否则 0）

按语言分别统计（zh_zh / zh_en / en_en），并输出每个 query 的原始 rank，
供误差分类与后续 holdout 扩展复用。

用法:
    python scripts/eval_rag_extended.py
    python scripts/eval_rag_extended.py --top-k 60 --final-k 20
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


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
                "must_contain": [str(s) for s in item.get("must_contain") or []],
                "language": name,
            })
    return rows


def _matches(source: str, relevant: str) -> bool:
    source_name = Path(str(source).replace("\\", "/")).name
    if source_name == relevant:
        return True
    relevant_id = Path(relevant).stem
    if "paper-" in source_name and relevant_id and relevant_id in source_name:
        return True
    return False


def _normalize(text: str) -> str:
    return " ".join(str(text or "").casefold().split())


def _fragment_hit(docs: list, must_contain: list[str]) -> bool | None:
    if not must_contain:
        return None
    for keyword in must_contain:
        needle = _normalize(keyword)
        if not needle:
            continue
        if not any(needle in _normalize(doc.page_content) for doc in docs):
            return False
    return True


def _metrics_for_query(docs: list, relevant: list[str]) -> dict:
    ranks = []
    for rank, doc in enumerate(docs, 1):
        source = str(doc.metadata.get("source") or "")
        if any(_matches(source, item) for item in relevant):
            ranks.append(rank)
    first = min(ranks) if ranks else None
    num_rel = len(relevant) or 1
    hits_in_k = lambda k: sum(1 for r in ranks if r <= k)  # noqa: E731

    def recall_at(k: int) -> float:
        return min(1.0, hits_in_k(k) / num_rel)

    mrr = (1.0 / first) if first else 0.0
    ndcg10 = (1.0 / math.log2(first + 1)) if (first and first <= 10) else 0.0
    return {
        "first_hit_rank": first,
        "recall@1": recall_at(1),
        "recall@3": recall_at(3),
        "recall@5": recall_at(5),
        "recall@10": recall_at(10),
        "recall@20": recall_at(20),
        "mrr": mrr,
        "ndcg@10": ndcg10,
    }


def _aggregate(results: list[dict]) -> dict:
    langs = ("zh_zh", "zh_en", "en_en")
    out: dict = {"overall": {}, "by_language": {}}
    for lang in ("__all__", *langs):
        group = results if lang == "__all__" else [r for r in results if r["language"] == lang]
        if not group:
            continue
        keys = ["recall@1", "recall@3", "recall@5", "recall@10", "recall@20", "mrr", "ndcg@10"]
        agg = {k: round(sum(r["metrics"][k] for r in group) / len(group), 4) for k in keys}
        frag = [r for r in group if r["fragment_hit"] is True]
        agg["hit_rate"] = round(sum(1 for r in group if r["metrics"]["recall@20"] >= 1.0) / len(group), 4)
        agg["fragment_hit_rate"] = round(len(frag) / len(group), 4) if group else None
        if lang == "__all__":
            out["overall"] = agg
        else:
            out["by_language"][lang] = agg
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Extended RAG evaluation (Recall/MRR/nDCG)")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--final-k", type=int, default=None)
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "eval" / "rag_ext" / "rag_extended.json"))
    args = parser.parse_args()

    from conflux import config as cfg
    from conflux.rag import create_vector_store, HybridRetriever

    raw = cfg.load()
    if args.top_k is not None:
        raw["retrieval"]["top_k"] = args.top_k
    if args.final_k is not None:
        raw["retrieval"]["final_k"] = args.final_k

    retriever = HybridRetriever(create_vector_store())
    rows = _load_queries()
    results = []
    for item in rows:
        docs = retriever.search(item["query"])
        m = _metrics_for_query(docs, item["relevant_sources"])
        fh = _fragment_hit(docs, item["must_contain"])
        results.append({
            "id": item["id"],
            "language": item["language"],
            "query": item["query"],
            "relevant_sources": item["relevant_sources"],
            "returned": len(docs),
            "fragment_hit": fh,
            "metrics": m,
        })

    aggregate = _aggregate(results)
    aggregate["top_k"] = raw["retrieval"]["top_k"]
    aggregate["final_k"] = raw["retrieval"]["final_k"]
    aggregate["query_count"] = len(results)
    payload = {"config": {k: aggregate[k] for k in ("top_k", "final_k", "query_count")}, "aggregate": aggregate, "results": results}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    print(f"wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
