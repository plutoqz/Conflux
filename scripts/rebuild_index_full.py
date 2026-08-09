"""重建全量本地 RAG 索引。

覆盖 data/documents 下的全部可检索内容：
- papers/papers/paper-{id}#{scope}.md 全部论文 summary/fulltext chunks（按文件名
  生成 paper_id/content_scope 元数据，不依赖 promotion manifest，避免漏掉
  未入库论文）；
- data/documents 根目录的 .md/.txt 普通资料（ESRI/NIST/wiki/AI 治理等），整篇截断索引，
  避免 wiki 长文档产生数万子块和过高 embedding 成本；
- 跳过 papers/pdfs 原始 PDF：对应论文文本已在 papers/papers/*.md 抽取并纳入 manifest。

用法:
    python scripts/rebuild_index_full.py            # 重建当前 collection
    python scripts/rebuild_index_full.py --dry-run  # 仅统计不写入
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.documents import Document  # noqa: E402

from conflux.config import get  # noqa: E402
from conflux.rag import clear_index, create_vector_store, index_documents  # noqa: E402


def _load_paper_documents(papers_dir: Path) -> tuple[list[Document], int]:
    """Load all paper summary/fulltext chunks from papers/papers/.

    ``paper-{arxiv_id}#{scope}.md`` files are already extraction-level chunks;
    they are indexed whole, not re-chunked.
    """

    docs: list[Document] = []
    skipped = 0
    for path in sorted(papers_dir.glob("paper-*.md")):
        name = path.name
        body = name[len("paper-"):]
        if "#" not in body:
            skipped += 1
            continue
        paper_id, scope = body.split("#", 1)
        scope = scope.removesuffix(".md")
        chunk_id = f"paper:{paper_id}#{scope}"
        docs.append(
            Document(
                page_content=path.read_text(encoding="utf-8", errors="replace"),
                metadata={
                    "source": str(path),
                    "source_type": "LocalPaper",
                    "paper_id": paper_id,
                    "chunk_id": chunk_id,
                    "citation_ref": f"LocalPaper:{paper_id}:{chunk_id}",
                    "content_scope": "summary" if scope == "summary" else "full_text",
                    "paper_section": scope,
                },
            )
        )
    return docs, skipped


def _load_plain_documents(root: Path) -> list[Document]:
    """Load root-level .md/.txt documents as truncated whole-document vectors.

    ``papers/`` is handled separately through the manifest.  Long wiki files
    are truncated to a bounded prefix so one document costs one embedding call
    while still carrying the topic surface needed for retrieval.
    """

    supported = {".md", ".txt"}
    max_chars = int(get("retrieval", "plain_doc_max_chars", default=8192))
    docs: list[Document] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue
        docs.append(
            Document(
                page_content=text[:max_chars],
                metadata={"source": path.name},
            )
        )
    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the full local RAG index")
    parser.add_argument("--dry-run", action="store_true", help="count documents without writing")
    args = parser.parse_args()

    root = PROJECT_ROOT / "data" / "documents"
    papers_dir = root / "papers" / "papers"
    paper_docs, skipped_papers = _load_paper_documents(papers_dir)
    plain_docs = _load_plain_documents(root)

    all_docs = [*paper_docs, *plain_docs]
    print(f"paper chunks: {len(paper_docs)} (skipped {skipped_papers})")
    print(f"plain documents: {len(plain_docs)} (whole-document, bounded prefix)")
    print(f"total documents to index: {len(all_docs)}")

    if args.dry_run:
        return 0

    vector_store = create_vector_store()
    clear_index(vector_store)
    indexed = index_documents(vector_store, all_docs)
    count = vector_store._collection.count()
    print(f"indexed: {indexed}; collection count: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
