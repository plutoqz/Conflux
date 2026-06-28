"""手动集成试跑脚本。

该脚本会调用真实模型和 embedding 服务，因此只应通过命令行显式运行：

    python scripts/test_run.py
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from langchain_core.documents import Document

from conflux.agent import create_sub_agent
from conflux.config import load
from conflux.graph_v2 import create_multi_agent_graph
from conflux.model_factory import create_chat_model
from conflux.rag import chunk_documents, clear_index, create_vector_store, index_documents
from conflux.rag.retriever import HybridRetriever
from conflux.report import write_report_artifacts
from conflux.tools import ask_model, create_rag_tool, search_web, set_model


def main() -> None:
    load()

    print("=" * 50)
    print("STEP 1: Indexing documents...")

    docs = []
    for fp in Path("data/documents").glob("*.txt"):
        docs.append(Document(page_content=fp.read_text(encoding="utf-8"), metadata={"source": fp.name}))
    print(f"  Read {len(docs)} documents")

    parents, children = chunk_documents(docs)
    print(f"  Chunked: {len(parents)} parents, {len(children)} children")

    vector_store = create_vector_store()
    clear_index(vector_store)
    indexed = index_documents(vector_store, children)
    print(f"  Indexed: {indexed} children chunks")

    print("\nSTEP 2: Creating three sub-agents...")
    reasoning_model = create_chat_model("reasoning")
    cheap_model = create_chat_model("cheap")
    set_model(reasoning_model)

    retriever = HybridRetriever(vector_store)
    rag_tool = create_rag_tool(retriever)

    rag_agent = create_sub_agent("rag", reasoning_model, rag_tool)
    web_agent = create_sub_agent("web", reasoning_model, search_web)
    model_agent = create_sub_agent("model", reasoning_model, ask_model)

    graph = create_multi_agent_graph(
        rag_agent,
        web_agent,
        model_agent,
        synthesizer_model=reasoning_model,
        arbitrator_model=cheap_model,
    )
    print("  Multi-agent graph compiled OK")

    query = "量子计算对密码学有哪些威胁？"
    print(f"\nSTEP 3: Running query: {query}")
    print("-" * 50)

    state = {
        "query": query,
        "rag_result": "",
        "web_result": "",
        "model_result": "",
        "_merged": "",
        "_arbitration": "",
        "_evidence_json": "",
        "_verified_answer": "",
        "_factcheck_status": "",
        "_pipeline_stage": "",
        "final_answer": "",
    }

    started_at = time.time()
    final_state = state
    for final_state in graph.stream(state, stream_mode="values"):
        for key in ["rag_result", "web_result", "model_result", "_arbitration", "final_answer", "_verified_answer"]:
            value = final_state.get(key)
            if value:
                print(f"  [{key}] {len(str(value))} chars")

    elapsed = time.time() - started_at
    print(f"\n  Latency: {elapsed:.1f}s")

    artifacts = write_report_artifacts(query, final_state)

    print("\n" + "=" * 50)
    print("FINAL ANSWER:")
    print("-" * 50)
    print(final_state.get("final_answer", "(no answer)")[:3000])
    print(f"\nMarkdown: {artifacts.markdown_path.resolve()}")
    print(f"HTML: {artifacts.html_path.resolve()}")


if __name__ == "__main__":
    main()
