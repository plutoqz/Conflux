"""R1 RAG retrieval ablation — S1 (chunk×embedding) + S2 (rerank) + cross-lingual (Step 5).

Plan: docs/plans/R1检索消融实验方案.md
Datasets: data/rag_eval/{zh_zh,zh_en,en_en}.yaml (new format)

Usage:
    python scripts/eval_rag_ablation.py --stage s1 [--embedding <m>] [--chunk 1024/256] [--reindex] [--dry-run]
    python scripts/eval_rag_ablation.py --stage s2 --embedding <best> --chunk <best>
    python scripts/eval_rag_ablation.py --stage cross
    python scripts/eval_rag_ablation.py --stage all
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── env overrides must be set before conflux.config.load() caches ──
os.environ["CONFLUX_RETRIEVAL__TOP_K"] = "80"
os.environ["CONFLUX_RETRIEVAL__FINAL_K"] = "60"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402
from langchain_core.documents import Document  # noqa: E402

EMBEDDINGS = ["text-embedding-v4", "bge-m3", "qwen3-embedding-8b", "jina-embeddings-v4"]
CHUNKS = ["512/128", "1024/256", "2048/512"]
RERANKERS = {
    "none": "无重排（下界）",
    "llm_judge": "LLM judge（SemanticReranker）",
    "bge-reranker-v2-m3-free": "Cross-Encoder bge-reranker-v2-m3-free",
    "jina-reranker-m0": "Cross-Encoder jina-reranker-m0",
}
DATASETS = {
    "zh_zh": {
        "labels": "data/rag_eval/zh_zh.yaml",
        "doc_dir": "data/documents",
        "label": "zh-zh",
        "min_cjk": 0.2,  # only Chinese docs (5 docs) for zh-zh scenario
    },
    "zh_en": {
        "labels": "data/rag_eval/zh_en.yaml",
        "doc_dir": "data/documents",
        "label": "zh-en",
        "skip_dirs": ("papers",),  # root .md only (esri docs)
    },
    "en_en": {
        "labels": "data/rag_eval/en_en.yaml",
        "doc_dir": "data/documents/papers",
        "label": "en-en",
    },
}
PERSIST = ROOT / "tmp" / "chroma_ablation"
OUT_DIR = ROOT / "reports" / "eval" / "rag_ablation"
METRICS = ["recall@10", "recall@20", "mrr@10", "ndcg@5", "ndcg@10"]


# ============================================================
# Embedding / store / indexing
# ============================================================

class DmxEmbeddings:
    """Minimal OpenAI-compatible embeddings wrapper.

    Bypasses langchain's tiktoken token-id path (dmxapi adapters for several
    models reject token-id input); always sends plain text lists in small
    batches under the API token limit.
    """

    def __init__(self, model: str, base_url: str, api_key: str, batch: int = 10):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.batch = batch

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            resp = self.client.embeddings.create(model=self.model, input=texts[i : i + self.batch])
            out.extend(item.embedding for item in resp.data)
        return out

    def embed_query(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding


def make_embedding(model: str):
    from conflux.config import get

    cfg = get("embedding") or {}
    base_url = cfg.get("base_url") or "https://www.dmxapi.cn/v1"
    api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    return DmxEmbeddings(model, base_url, api_key)


def get_store(embedding_model, collection: str, reset: bool = False):
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from langchain_chroma import Chroma

    PERSIST.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(PERSIST),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(collection)
        except Exception:
            pass
    return Chroma(
        client=client,
        collection_name=collection,
        embedding_function=embedding_model,
    )


def _load_documents_from_dir(doc_dir: Path, min_cjk: float | None = None, skip_dirs: tuple[str, ...] = ()) -> list[Document]:
    supported = {".txt", ".md", ".pdf"}
    docs: list[Document] = []
    for path in sorted(p for p in doc_dir.rglob("*") if p.is_file() and p.suffix.lower() in supported):
        if any(part in skip_dirs for part in path.parts):
            continue
        source = path.relative_to(doc_dir).as_posix()
        try:
            if path.suffix.lower() == ".pdf":
                continue  # PDF extraction is out of scope for R1 (summary .md used)
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not text.strip():
            continue
        if min_cjk:
            cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff") / max(1, len(text))
            if cjk < min_cjk:
                continue
        docs.append(Document(page_content=text, metadata={"source": source}))
    return docs


def index_dataset(store, doc_dir: Path, parent_size: int, child_size: int, batch: int = 1000,
                  min_cjk: float | None = None, skip_dirs: tuple[str, ...] = ()) -> int:
    from conflux.rag import chunk_documents

    documents = _load_documents_from_dir(doc_dir, min_cjk=min_cjk, skip_dirs=skip_dirs)
    parents, children = chunk_documents(documents, parent_size=parent_size, child_size=child_size)
    for start in range(0, len(children), batch):
        store.add_documents(children[start : start + batch])
    return len(children)


def collection_count(store) -> int:
    try:
        return store._collection.count()
    except Exception:
        return 0


# ============================================================
# Retrieval / aggregation / grading
# ============================================================

def retrieve(store, query: str) -> list[Document]:
    from conflux.rag.retriever import HybridRetriever

    return HybridRetriever(store).search(query)


def aggregate_docs(docs: list[Document]) -> dict[str, dict]:
    """Aggregate chunks to doc level: {source_basename: {score, text}}."""
    agg: dict[str, dict] = {}
    for doc in docs:
        meta = doc.metadata or {}
        source = str(meta.get("source") or "")
        key = Path(source).name
        score = float(meta.get("rrf_score") or 0.0)
        entry = agg.get(key)
        if entry is None:
            agg[key] = {"score": score, "text": doc.page_content, "chunks": 1}
        else:
            entry["score"] = max(entry["score"], score)
            entry["text"] += "\n" + doc.page_content
            entry["chunks"] += 1
    return agg


def label_relevant_names(label: dict) -> list[str]:
    return [Path(s).name for s in label["relevant_sources"]]


def grade_doc(source_name: str, text: str, label: dict) -> int:
    """R1 grading: 3 = source match + >=50% must_contain; 2 = source match;
    1 = no source match but partial must_contain; 0 = nothing."""
    kws = label["must_contain"] or []
    hits = sum(1 for k in kws if k in text)
    if source_name in label_relevant_names(label):
        return 3 if hits >= max(2, len(kws) * 0.5) else 2
    return 1 if hits else 0


def load_labels(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_qrels(labels: list[dict], doc_dir: Path) -> dict:
    """qrels: qid -> {doc_basename: 2|3} based on full-document keyword presence."""
    qrels: dict[str, dict] = {}
    for label in labels:
        qrels[label["id"]] = {}
        for src in label["relevant_sources"]:
            path = doc_dir / src
            if not path.exists():
                matches = list(doc_dir.rglob(Path(src).name))
                path = matches[0] if matches else None
            if path is None or not path.exists():
                print(f"  [warn] label source not found: {src}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            kws = label["must_contain"] or []
            hits = sum(1 for k in kws if k in text)
            grade = 3 if hits >= max(2, len(kws) * 0.5) else 2
            qrels[label["id"]][Path(src).name] = grade
    return qrels


def build_run(rankings: dict[str, list[Document]]) -> dict:
    """Build a run keyed by doc basename with rank-position scores.

    Position-based scores (1/(rank+1)) preserve the exact ordering of the
    returned documents — which is what rerankers change — while being
    equivalent for ranking metrics (recall/mrr/ndcg only depend on order).
    """
    run: dict[str, dict] = {}
    for qid, docs in rankings.items():
        seen: dict[str, float] = {}
        for rank, doc in enumerate(docs):
            source = str((doc.metadata or {}).get("source") or "")
            name = Path(source).name
            if name and name not in seen:
                seen[name] = 1.0 / (rank + 1)
        run[qid] = seen
    return run


def evaluate_ranx(qrels: dict, run: dict) -> dict:
    from ranx import Qrels, Run, evaluate

    qrels_obj = Qrels(qrels)
    run_obj = Run(run)
    return evaluate(qrels_obj, run_obj, metrics=METRICS)


# ============================================================
# Rerankers
# ============================================================

def rerank_none(scored_docs, limit=None):
    return scored_docs[:limit] if limit else scored_docs


def rerank_llm_judge(query, scored_docs, limit=None):
    from conflux.model_factory import create_chat_model
    from conflux.rag.reranker import SemanticReranker

    candidates = scored_docs[:limit] if limit else scored_docs
    reranker = SemanticReranker(create_chat_model("flash"), batch_size=16)
    return reranker.rerank(query, candidates, limit=len(candidates))


class CrossEncoderReranker:
    """POST /v1/rerank wrapper for bge-reranker-v2-m3-free / jina-reranker-m0."""

    def __init__(self, model: str, base_url: str = "https://www.dmxapi.cn/v1"):
        self.model = model
        self.base_url = base_url
        from conflux.config import get

        cfg = get("embedding") or {}
        self.api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")

    def rerank(self, query, scored_docs, *, limit=None):
        candidates = scored_docs[:limit] if limit else scored_docs
        if not candidates:
            return []
        payload = {
            "model": self.model,
            "query": query,
            "documents": [str(d["doc"].page_content)[:4000] for d in candidates],
            "top_n": len(candidates),
        }
        req = urllib.request.Request(
            f"{self.base_url}/rerank",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"rerank {self.model} failed: {e.code} {e.read().decode('utf-8')[:200]}")
        results = sorted(body.get("results", []), key=lambda r: r.get("relevance_score", 0.0), reverse=True)
        ordered = []
        for item in results:
            idx = int(item.get("index", 0))
            if 0 <= idx < len(candidates):
                src = dict(candidates[idx])
                src["score"] = float(item.get("relevance_score", 0.0))
                ordered.append(src)
        return ordered


def make_reranker(name: str):
    if name == "none":
        return rerank_none
    if name == "llm_judge":
        return rerank_llm_judge
    reranker = CrossEncoderReranker(name)

    def _rerank(query, scored_docs, limit=None):
        return reranker.rerank(query, scored_docs, limit=limit)

    return _rerank


# ============================================================
# Run helpers
# ============================================================

def run_one_retrieval(store, labels: list[dict], rerank_name: str = "none", top_k: int = 60) -> dict:
    reranker = make_reranker(rerank_name)
    rankings: dict[str, list[Document]] = {}
    for label in labels:
        query = str(label["query"])
        docs = retrieve(store, query)
        scored = [
            {
                "doc": doc,
                "score": float((doc.metadata or {}).get("rrf_score") or 0.0),
                "breakdown": {
                    "dense_score": (doc.metadata or {}).get("dense_score"),
                    "bm25_score": (doc.metadata or {}).get("bm25_score"),
                    "rrf_score": (doc.metadata or {}).get("rrf_score"),
                },
            }
            for doc in docs[:top_k]
        ]
        if rerank_name != "none":
            ordered = reranker(query, scored, limit=top_k)
            rankings[label["id"]] = [item["doc"] for item in ordered]
        else:
            rankings[label["id"]] = [item["doc"] for item in scored]
    return rankings


def config_key(embedding: str, chunk: str) -> str:
    return f"{embedding}|{chunk}"


def parse_chunk(chunk: str) -> tuple[int, int]:
    parent, child = chunk.split("/")
    return int(parent), int(child)


def best_of_s1(s1_results: dict) -> tuple[str, str]:
    """Pick best (embedding, chunk) by recall@20 then ndcg@10."""
    ranked = sorted(
        s1_results.items(),
        key=lambda kv: (kv[1]["metrics"].get("recall@20", 0.0), kv[1]["metrics"].get("ndcg@10", 0.0)),
        reverse=True,
    )
    return ranked[0][0].split("|")


# ============================================================
# Stages
# ============================================================

def run_s1(args) -> dict:
    from conflux.config import load as config_load

    config_load()
    dataset = DATASETS[args.dataset]
    labels = load_labels(ROOT / dataset["labels"])
    doc_dir = ROOT / dataset["doc_dir"]
    qrels = build_qrels(labels, doc_dir)

    embeddings = [args.embedding] if args.embedding else EMBEDDINGS
    chunks = [args.chunk] if args.chunk else CHUNKS
    results: dict[str, dict] = {}
    for emb in embeddings:
        for chunk in chunks:
            parent, child = parse_chunk(chunk)
            key = config_key(emb, chunk)
            collection = f"{dataset['label'].replace('-', '_')}-{emb}-{parent}-{child}"
            print(f"[S1] {key} ... ", end="", flush=True)
            t0 = time.time()
            emb_model = make_embedding(emb)
            store = get_store(emb_model, collection, reset=args.reindex)
            if args.reindex or collection_count(store) == 0:
                n = index_dataset(store, doc_dir, parent, child,
                                  min_cjk=dataset.get("min_cjk"), skip_dirs=dataset.get("skip_dirs", ()))
                print(f"indexed {n} chunks, ", end="", flush=True)
            rankings = run_one_retrieval(store, labels, rerank_name="none")
            metrics = evaluate_ranx(qrels, build_run(rankings))
            elapsed = time.time() - t0
            results[key] = {
                "embedding": emb, "chunk": chunk, "dataset": args.dataset,
                "metrics": metrics, "elapsed_s": round(elapsed, 1),
            }
            print(f"recall@20={metrics.get('recall@20', 0):.3f} ndcg@10={metrics.get('ndcg@10', 0):.3f} ({elapsed:.0f}s)")
    return results


def run_s2(args, best_embedding: str, best_chunk: str) -> dict:
    from conflux.config import load as config_load

    config_load()
    dataset = DATASETS[args.dataset]
    labels = load_labels(ROOT / dataset["labels"])
    doc_dir = ROOT / dataset["doc_dir"]
    qrels = build_qrels(labels, doc_dir)
    parent, child = parse_chunk(best_chunk)
    collection = f"{dataset['label'].replace('-', '_')}-{best_embedding}-{parent}-{child}"
    store = get_store(make_embedding(best_embedding), collection)
    if collection_count(store) == 0:
        index_dataset(store, doc_dir, parent, child,
                      min_cjk=dataset.get("min_cjk"), skip_dirs=dataset.get("skip_dirs", ()))

    results: dict[str, dict] = {}
    rerankers = (args.rerankers or "").split(",") if args.rerankers else list(RERANKERS)
    for name in rerankers:
        name = name.strip()
        if name not in RERANKERS:
            continue
        print(f"[S2] {name} ... ", end="", flush=True)
        t0 = time.time()
        rankings = run_one_retrieval(store, labels, rerank_name=name)
        metrics = evaluate_ranx(qrels, build_run(rankings))
        elapsed = time.time() - t0
        results[name] = {
            "reranker": name, "embedding": best_embedding, "chunk": best_chunk,
            "metrics": metrics, "elapsed_s": round(elapsed, 1),
        }
        print(f"recall@20={metrics.get('recall@20', 0):.3f} ndcg@10={metrics.get('ndcg@10', 0):.3f} ({elapsed:.0f}s)")
    return results


def run_cross(args, s1_results: dict) -> dict:
    from conflux.config import load as config_load

    config_load()
    best_emb, best_chunk = best_of_s1(s1_results)
    print(f"[cross] global best from S1: {best_emb} / {best_chunk}")
    results: dict[str, dict] = {}

    # 5a: 4 embeddings x zh_en (each on its own S1-best chunk)
    zh_en = DATASETS["zh_en"]
    labels = load_labels(ROOT / zh_en["labels"])
    doc_dir = ROOT / zh_en["doc_dir"]
    qrels = build_qrels(labels, doc_dir)
    for emb in EMBEDDINGS:
        emb_best_chunk = best_chunk
        # per-embedding best chunk from S1 results
        candidates = {k.split("|")[1]: v for k, v in s1_results.items() if k.startswith(emb + "|")}
        if candidates:
            emb_best_chunk = sorted(candidates.items(), key=lambda kv: kv[1]["metrics"].get("recall@20", 0), reverse=True)[0][0]
        parent, child = parse_chunk(emb_best_chunk)
        collection = f"zh_en-{emb}-{parent}-{child}"
        store = get_store(make_embedding(emb), collection)
        if collection_count(store) == 0:
            index_dataset(store, doc_dir, parent, child,
                          min_cjk=zh_en.get("min_cjk"), skip_dirs=zh_en.get("skip_dirs", ()))
        print(f"[cross] zh_en {emb} @ {emb_best_chunk} ... ", end="", flush=True)
        t0 = time.time()
        rankings = run_one_retrieval(store, labels, rerank_name="none")
        metrics = evaluate_ranx(qrels, build_run(rankings))
        results[f"zh_en|{emb}|{emb_best_chunk}"] = {
            "dataset": "zh_en", "embedding": emb, "chunk": emb_best_chunk,
            "metrics": metrics, "elapsed_s": round(time.time() - t0, 1),
        }
        print(f"recall@20={metrics.get('recall@20', 0):.3f}")

    # 5b: global best config x en_en
    en_en = DATASETS["en_en"]
    labels = load_labels(ROOT / en_en["labels"])
    doc_dir = ROOT / en_en["doc_dir"]
    qrels = build_qrels(labels, doc_dir)
    parent, child = parse_chunk(best_chunk)
    collection = f"en_en-{best_emb}-{parent}-{child}"
    store = get_store(make_embedding(best_emb), collection)
    if collection_count(store) == 0:
        index_dataset(store, doc_dir, parent, child,
                      min_cjk=en_en.get("min_cjk"), skip_dirs=en_en.get("skip_dirs", ()))
    print(f"[cross] en_en {best_emb} @ {best_chunk} ... ", end="", flush=True)
    t0 = time.time()
    rankings = run_one_retrieval(store, labels, rerank_name="none")
    metrics = evaluate_ranx(qrels, build_run(rankings))
    results[f"en_en|{best_emb}|{best_chunk}"] = {
        "dataset": "en_en", "embedding": best_emb, "chunk": best_chunk,
        "metrics": metrics, "elapsed_s": round(time.time() - t0, 1),
    }
    print(f"recall@20={metrics.get('recall@20', 0):.3f}")
    return results


# ============================================================
# Reports
# ============================================================

def fmt_metrics(m: dict) -> str:
    return "  ".join(f"{k}={m.get(k, 0):.3f}" for k in METRICS)


def write_report(name: str, title: str, rows: list[tuple[str, dict]], extra: str = "") -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md = [f"# {title}", "", "| 配置 | " + " | ".join(METRICS) + " |", "|---|---" + "---|" * len(METRICS)]
    for label, item in rows:
        m = item["metrics"]
        md.append(f"| {label} | " + " | ".join(f"{m.get(k, 0):.3f}" for k in METRICS) + " |")
    if extra:
        md += ["", extra]
    md += ["", f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"]
    path = OUT_DIR / name
    path.write_text("\n".join(md), encoding="utf-8")
    json_path = OUT_DIR / name.replace(".md", ".json")
    json_path.write_text(json.dumps({r[0]: r[1] for r in rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="R1 RAG retrieval ablation")
    parser.add_argument("--stage", choices=["s1", "s2", "cross", "all"], default="all")
    parser.add_argument("--embedding", choices=EMBEDDINGS, default=None)
    parser.add_argument("--chunk", choices=CHUNKS, default=None)
    parser.add_argument("--dataset", choices=list(DATASETS), default="zh_zh")
    parser.add_argument("--rerankers", default=None, help="comma list for S2 (default: all 4)")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="single embedding/chunk, 2 labels only")
    args = parser.parse_args()

    if args.dry_run:
        args.embedding = args.embedding or "bge-m3"
        args.chunk = args.chunk or "1024/256"

    results: dict = {}
    if args.stage in ("s1", "all"):
        s1 = run_s1(args)
        results["s1"] = s1
        best_emb, best_chunk = best_of_s1(s1)
        print(f"\n>>> S1 best: {best_emb} / {best_chunk} (recall@20={s1[config_key(best_emb, best_chunk)]['metrics'].get('recall@20'):.3f})\n")
        rows = [(k, v) for k, v in s1.items()]
        path = write_report("s1_report.md", f"R1 S1 — 底座选择（{args.dataset}）", rows,
                            extra=f"**S1 最佳配置**：`{best_emb}` / `{best_chunk}`（主指标 Recall@20，辅助 NDCG@10）")
        print(f"report: {path}")
    else:
        s1 = results.get("s1", {})
        best_emb, best_chunk = args.embedding or "bge-m3", args.chunk or "1024/256"

    if args.stage in ("s2", "all"):
        if args.stage == "all":
            best_emb, best_chunk = best_of_s1(results["s1"])
        s2 = run_s2(args, best_emb, best_chunk)
        results["s2"] = s2
        rows = [(f"{RERANKERS[k]}", v) for k, v in s2.items()]
        path = write_report("s2_report.md", f"R1 S2 — 重排消融（底座 {best_emb} / {best_chunk}，{args.dataset}）", rows)
        print(f"report: {path}")

    if args.stage in ("cross", "all"):
        s1_for_cross = results.get("s1")
        if s1_for_cross is None:
            s1_path = OUT_DIR / "s1_report.json"
            if s1_path.exists():
                s1_for_cross = json.loads(s1_path.read_text(encoding="utf-8"))
            else:
                print("[cross] requires S1 results; run --stage s1 first or use --stage all")
                return 1
        cross = run_cross(args, s1_for_cross)
        results["cross"] = cross
        rows = [(k, v) for k, v in cross.items()]
        path = write_report("cross_report.md", "R1 Step5 — 跨语言验证（zh-en 4 模型对比 + en-en 最佳配置）", rows)
        print(f"report: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
