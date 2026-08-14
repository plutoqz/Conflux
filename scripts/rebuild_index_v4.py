"""重建知识库到 text-embedding-v4（1024 维）。

背景：config.yaml 声明 embedding.model=text-embedding-v4，但 .env 曾用
CONFLUX_EMBEDDING__MODEL 覆盖为 text-embedding-3-small（1536 维），
活跃 collection conflux_docs 的 48,745 条全部是 3-small。本脚本把
conflux_docs 原样保留（作为回滚点），新建
conflux_docs__text-embedding-v4__{ts} 并依次重建：

1. data/documents 下 72 个 md（wiki/esri/nist + papers/#summary）
2. 论文 PDF 全文页（promote_inbox 重放本地 PDF；不下载）
3. E1 代码块（conflux 自身 src）

用法：
    python scripts/rebuild_index_v4.py [--keep-old] [--skip-papers] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux import config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-old", action="store_true",
                        help="保留旧 conflux_docs（默认保留）")
    parser.add_argument("--skip-papers", action="store_true",
                        help="跳过 PDF 论文全文重建（只有 md 时用）")
    parser.add_argument("--collection", default="",
                        help="写入已有 collection（不新建）；默认新建时间戳 collection")
    args = parser.parse_args()

    started = time.perf_counter()
    active = str(config.get("vector_store", "collection_name", default="conflux_docs"))
    model = str(config.get("embedding", "model", default="text-embedding-v4"))
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-._") or "embedding"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    new_name = args.collection or f"{active}__{slug}__{stamp}"
    print(f"[rebuild] 目标 collection：{new_name}（{'复用已有' if args.collection else '新建'}）")

    from conflux.rag.indexer import create_vector_store, index_documents
    from conflux.workbench.server import _load_knowledge_documents, save_workbench_env

    # 1) 创建空新 collection 并切换激活（config.override 进程内生效）；
    #    复用已有 collection 时跳过创建（直接写）。
    if not args.collection:
        with config.override({
            "CONFLUX_VECTOR_STORE__COLLECTION_NAME": new_name,
            "CONFLUX_EMBEDDING__MODEL": model,
        }):
            store = create_vector_store()
            store._collection.count()
        print(f"[rebuild] 新建 collection：{new_name}")

    # 2) md 知识文档（先按项目文档一致的分块链切块，避免单条超 v4 的 33k 上限）
    from langchain_core.documents import Document
    from conflux.rag.chunker import chunk_document

    source_dir = PROJECT_ROOT / "data" / "documents"
    raw_docs = _load_knowledge_documents(source_dir)
    docs: list[Document] = []
    for raw in raw_docs:
        parents, children = chunk_document(raw)
        docs.extend(parents)
        docs.extend(children)
    print(f"[rebuild] data/documents md: {len(raw_docs)} 个 → {len(docs)} 块")
    with config.override({
        "CONFLUX_VECTOR_STORE__COLLECTION_NAME": new_name,
        "CONFLUX_EMBEDDING__MODEL": model,
    }):
        indexed_md = index_documents(create_vector_store(), docs)
    print(f"[rebuild] md 索引 +{indexed_md}")

    # 3) data/documents/papers 下 PDF 逐页，且按 parent/child 双粒度分块
    #    （与旧库 papers/{file}#page-N#p{m}#c{n} 同构，页面检索粒度对齐）。
    from conflux.__main__ import _read_pdf_documents
    from conflux.rag.chunker import chunk_document
    from langchain_core.documents import Document as _Document
    pdf_docs: list[Document] = []
    papers_root = source_dir / "papers"
    for pdf in sorted(papers_root.rglob("*.pdf")):
        rel = pdf.relative_to(source_dir).as_posix()
        for page in _read_pdf_documents(pdf, rel):
            parents, children = chunk_document(page)
            pdf_docs.extend(parents)
            pdf_docs.extend(children)
    print(f"[rebuild] papers PDF 页: {len(pdf_docs)} 个（含分块）")
    with config.override({
        "CONFLUX_VECTOR_STORE__COLLECTION_NAME": new_name,
        "CONFLUX_EMBEDDING__MODEL": model,
    }):
        indexed_pdf = index_documents(create_vector_store(), pdf_docs)
    print(f"[rebuild] PDF 页索引 +{indexed_pdf}")

    # 4) E1 代码块
    from conflux.code_qa import index_project_code
    code_result = None
    with config.override({
        "CONFLUX_VECTOR_STORE__COLLECTION_NAME": new_name,
        "CONFLUX_EMBEDDING__MODEL": model,
    }):
        from conflux.project_registry.models import ProjectDefinition
        project = ProjectDefinition(id="conflux-self", name="Conflux", path=str(PROJECT_ROOT))
        code_result = index_project_code(None, project, root_dir=str(PROJECT_ROOT / "src"))
    print(f"[rebuild] code: {code_result}")

    # 5) 切换激活 collection（写 .env.workbench）
    from conflux.workbench.config_store import save_workbench_env
    written = save_workbench_env(
        embedding_model=model,
        vector_collection_name=new_name,
    )
    print(f"[rebuild] 激活 collection 已切换为 {new_name}（.env.workbench 写入 {written} 行）")

    print(f"[rebuild] 完成，耗时 {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())