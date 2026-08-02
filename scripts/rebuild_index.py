"""重建 ChromaDB 向量索引 — 使用当前 config.yaml 中的 embedding 和 chunk 配置。

用法:
    python scripts/rebuild_index.py
    python scripts/rebuild_index.py --dry-run   # 仅列出将要索引的文档，不实际写入
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path for `from conflux.*` imports.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.documents import Document
from conflux.rag.indexer import create_vector_store, index_documents


def load_documents_from_manifest(
    manifest_path: Path,
) -> tuple[list[Document], int]:
    """从 paper_promotion_manifest.json 重建 Document 列表。"""
    if not manifest_path.exists():
        print(f"[ERROR] manifest 文件不存在: {manifest_path}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: list[dict] = manifest.get("documents", [])
    if not entries:
        print("[ERROR] manifest 中无文档记录")
        sys.exit(1)

    docs: list[Document] = []
    skipped = 0

    for entry in entries:
        file_path = Path(entry["path"])
        if not file_path.exists():
            print(f"  [SKIP] 文件不存: {file_path}")
            skipped += 1
            continue

        content = file_path.read_text(encoding="utf-8")
        metadata = {
            "chunk_id": entry.get("chunk_id", ""),
            "citation_ref": entry.get("citation_ref", ""),
            "paper_section": entry.get("paper_section", ""),
            "full_text_requested": entry.get("full_text_requested", False),
            "full_text_downloaded": entry.get("full_text_downloaded", False),
            "full_text_extracted": entry.get("full_text_extracted", False),
            "full_text_indexed": entry.get("full_text_indexed", False),
            "source": str(file_path),
        }
        docs.append(Document(page_content=content, metadata=metadata))

    return docs, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="重建 ChromaDB 向量索引")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅列出文档，不写入 ChromaDB",
    )
    args = parser.parse_args()

    manifest_path = PROJECT_ROOT / "data" / "documents" / "papers" / "paper_promotion_manifest.json"

    print("=" * 60)
    print("ChromaDB 索引重建")
    print("=" * 60)

    # 1. 加载文档
    print(f"\n[1/3] 从 manifest 加载文档...\n  {manifest_path}")
    documents, skipped = load_documents_from_manifest(manifest_path)
    print(f"  加载了 {len(documents)} 篇文档" + (f"，跳过 {skipped} 个缺失文件" if skipped else ""))

    if args.dry_run:
        print("\n  [DRY-RUN] 文档列表:")
        for doc in documents:
            chunk_id = doc.metadata.get("chunk_id", "?")
            section = doc.metadata.get("paper_section", "?")
            chars = len(doc.page_content)
            print(f"    {chunk_id:50s}  section={section:20s}  chars={chars}")
        print(f"\n  共 {len(documents)} 篇，实际写入将清空旧索引后重新索引。")
        return

    # 2. 创建向量库 + 清空
    print("\n[2/3] 创建向量库连接并删除旧 collection...")
    vector_store = create_vector_store()
    # Embedding dimension changed (text-embedding-3-small=1536 → v4=1024);
    # delete the entire collection so ChromaDB creates a fresh one.
    try:
        from conflux.config import get
        persist_dir = get("vector_store", "persist_dir", default="./data/chroma_db")
        collection_name = get("vector_store", "collection_name", default="conflux_docs")
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        client.delete_collection(collection_name)
        print(f"  已删除 collection '{collection_name}'。")
    except Exception:
        pass
    # Recreate vector_store so it picks up the new collection + embedding dims
    vector_store = create_vector_store()
    print("  新 collection 已创建。")

    # 3. 重建索引
    print(f"\n[3/3] 写入 {len(documents)} 篇文档...")
    indexed = index_documents(vector_store, documents)
    print(f"  完成: {indexed} 个 chunk 已写入 ChromaDB。")

    # 验证
    try:
        existing = vector_store.get()
        count = len(existing.get("ids", []))
        print(f"  验证: collection 当前共 {count} 个向量。")
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("重建完成。")
    print("=" * 60)


if __name__ == "__main__":
    main()
