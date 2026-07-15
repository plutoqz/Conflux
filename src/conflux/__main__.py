"""CLI entrypoint for Conflux."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from langchain_core.documents import Document

from .agent import ResearchAgent, create_sub_agent
from .checkpointing import create_checkpointer, graph_config
from .config import load as load_config
from .graph import create_graph
from .graph_v2 import create_multi_agent_graph
from .model_factory import create_chat_model, validate_embedding_credentials, validate_runtime_credentials
from .rag import HybridRetriever, chunk_documents, clear_index, create_vector_store, index_documents
from .report import write_report_artifacts
from .tools import ask_model, create_rag_tool, search_web, set_model
from .trace import event_from_state_key, new_run_id, write_run_summary, write_trace_jsonl


def _clean_text(text: str) -> str:
    """Remove invalid Unicode code points that vector stores cannot encode."""

    return text.encode("utf-8", errors="ignore").decode("utf-8")


def _configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _read_pdf_documents(path: Path, source: str) -> list[Document]:
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"Warning: skipping PDF '{path.name}' — pypdf is not installed. Install it with: pip install pypdf")
        return []

    reader = PdfReader(str(path))
    documents = []
    for page_idx, page in enumerate(reader.pages, start=1):
        text = _clean_text(page.extract_text() or "")
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": f"{source}#page-{page_idx}", "file": source, "page": page_idx},
                )
            )
    return documents


def _load_index_documents(doc_path: Path) -> list[Document]:
    supported_suffixes = {".txt", ".md", ".pdf"}
    files = sorted(path for path in doc_path.rglob("*") if path.is_file() and path.suffix.lower() in supported_suffixes)
    documents = []
    for path in files:
        source = path.relative_to(doc_path).as_posix()
        suffix = path.suffix.lower()
        if suffix in (".txt", ".md"):
            text = _clean_text(path.read_text(encoding="utf-8"))
            documents.append(Document(page_content=text, metadata={"source": source}))
        elif suffix == ".pdf":
            documents.extend(_read_pdf_documents(path, source))
    return documents


def index_command(docs_dir: str) -> None:
    """Index local .txt/.md/.pdf documents into the configured vector store."""

    load_config()
    credential_problems = validate_embedding_credentials()
    if credential_problems:
        print("Error: building the RAG index requires embedding credentials.")
        for problem in credential_problems:
            print(f"- {problem}")
        print("\nConfigure OPENAI_API_KEY or CONFLUX_EMBEDDING__API_KEY.")
        sys.exit(2)

    doc_path = Path(docs_dir)
    if not doc_path.exists():
        print(f"Error: directory does not exist: {doc_path}")
        sys.exit(1)

    documents = _load_index_documents(doc_path)
    if not documents:
        print(f"Warning: no .txt, .md, or .pdf files found under {doc_path}")
        return

    print(f"Read {len(documents)} documents.")

    parents, children = chunk_documents(documents)
    print(f"Chunked into {len(parents)} parent chunks and {len(children)} child chunks.")

    vector_store = create_vector_store()
    clear_index(vector_store)
    indexed = index_documents(vector_store, children)
    print(f"Indexed {indexed} child chunks into the vector store.")


def _empty_multi_agent_state(
    query: str,
    *,
    run_id: str | None = None,
    thread_id: str | None = None,
    checkpoint_backend: str = "none",
    resumed: bool = False,
) -> dict:
    run_id = run_id or new_run_id()
    thread_id = thread_id or run_id
    return {
        "query": query,
        "rag_result": "",
        "web_result": "",
        "model_result": "",
        "_merged": "",
        "_arbitration": "",
        "_evidence_json": "",
        "_source_statuses": {},
        "_verified_answer": "",
        "_factcheck_status": "",
        "_factcheck_report": "",
        "_deep_research": "",
        "_run_summary": {},
        "_quality_report": {},
        "_pipeline_stage": "",
        "_run_id": run_id,
        "_thread_id": thread_id,
        "_checkpoint_backend": checkpoint_backend,
        "_resumed": resumed,
        "_review_status": "",
        "final_answer": "",
    }


def query_command(
    query: str,
    mode: str = "phase2",
    output_dir: str = "reports",
    *,
    thread_id: str | None = None,
    resume: str | None = None,
    checkpoint_backend: str = "none",
    stream_events: bool = False,
    trace_dir: str | None = None,
    run_id: str | None = None,
) -> dict:
    """Run one research query."""

    load_config()
    credential_problems = validate_runtime_credentials()
    if credential_problems:
        print("Error: real API execution is missing required credentials.")
        for problem in credential_problems:
            print(f"- {problem}")
        print("\nConfigure OPENAI_API_KEY, or source-specific CONFLUX_* API key overrides.")
        sys.exit(2)

    print("-> Initializing models...")
    reasoning_model = create_chat_model("reasoning")
    cheap_model = create_chat_model("cheap")
    set_model(reasoning_model)

    vector_store = create_vector_store()
    retriever = HybridRetriever(vector_store)
    rag_tool = create_rag_tool(retriever)

    run_id = run_id or new_run_id()
    effective_thread_id = resume or thread_id or run_id
    checkpoint = create_checkpointer(checkpoint_backend)
    print(f"-> Mode: {mode}")
    print(f"-> Run id: {run_id}")
    print(f"-> Thread id: {effective_thread_id}")
    print(f"-> Checkpoint backend: {checkpoint.backend}")

    if mode == "phase1":
        tools = [rag_tool, search_web, ask_model]
        agent = ResearchAgent(reasoning_model, tools)
        graph = create_graph(agent)
        initial_state = {
            "query": query,
            "messages": agent.build_messages(query),
            "final_answer": "",
            "iteration_count": 0,
        }
        final_state, trace_events = _run_phase1_graph(graph, initial_state, query)
    else:
        rag_agent = create_sub_agent("rag", reasoning_model, rag_tool)
        web_agent = create_sub_agent("web", reasoning_model, search_web)
        model_agent = create_sub_agent("model", reasoning_model, ask_model)
        graph = create_multi_agent_graph(
            rag_agent,
            web_agent,
            model_agent,
            synthesizer_model=reasoning_model,
            arbitrator_model=cheap_model,
            checkpointer=checkpoint.checkpointer,
        )
        initial_state = _empty_multi_agent_state(
            query,
            run_id=run_id,
            thread_id=effective_thread_id,
            checkpoint_backend=checkpoint.backend,
            resumed=bool(resume),
        )
        final_state, trace_events = _run_phase2_graph(
            graph,
            initial_state,
            query,
            stream_events=stream_events,
            thread_id=effective_thread_id,
        )

    answer = final_state.get("final_answer", "")
    artifacts = None
    if answer:
        print(f"\n{answer}\n")
        artifacts = write_report_artifacts(query, final_state, output_dir=output_dir)
        print(f"Markdown report: {artifacts.markdown_path.resolve()}")
        print(f"HTML report: {artifacts.html_path.resolve()}")
    else:
        print("\nWarning: no final answer was generated. Check API, embedding, and tool configuration.\n")

    trace_root = Path(trace_dir or output_dir)
    trace_path = trace_root / f"{run_id}.trace.jsonl"
    summary_path = trace_root / f"{run_id}.summary.json"
    write_trace_jsonl(trace_events, trace_path)
    summary = dict(final_state.get("_run_summary") or {})
    summary.update({
        "run_id": run_id,
        "thread_id": effective_thread_id,
        "query": query,
        "final_answer": answer[:2000] if answer else "",
        "checkpoint_backend": checkpoint.backend,
        "resumed": bool(resume),
        "trace_path": str(trace_path),
        "report_md_path": str(artifacts.markdown_path.resolve()) if artifacts else "",
        "report_html_path": str(artifacts.html_path.resolve()) if artifacts else "",
        "source_statuses": {
            source: payload.get("status")
            for source, payload in (final_state.get("_source_statuses") or {}).items()
        },
        "factcheck_status": final_state.get("_factcheck_status"),
        "quality": final_state.get("_quality_report") or {},
    })
    write_run_summary(summary, summary_path)
    print(f"Trace JSONL: {trace_path.resolve()}")
    print(f"Run summary: {summary_path.resolve()}")

    return final_state


def _run_phase1_graph(graph, initial_state: dict, query: str) -> tuple[dict, list]:
    print(f"-> Starting single-agent research: {query}\n")
    print("=" * 60)
    event = initial_state
    step = 0
    for event in graph.stream(initial_state, stream_mode="values"):
        step += 1
        messages = event.get("messages", [])
        if messages:
            last_msg = messages[-1]
            prefix = f"[Step {step}]"
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tool_call in last_msg.tool_calls:
                    print(f"{prefix} tool: {tool_call['name']}({tool_call['args']})")
            elif hasattr(last_msg, "content") and last_msg.content:
                content = last_msg.content
                if isinstance(content, str) and len(content) > 200:
                    content = content[:200] + "..."
                print(f"{prefix} {type(last_msg).__name__}: {content}")
    print("=" * 60)
    return event, []


def _run_phase2_graph(
    graph,
    initial_state: dict,
    query: str,
    *,
    stream_events: bool = False,
    thread_id: str | None = None,
) -> tuple[dict, list]:
    print(f"-> Starting three-source multi-agent research: {query}\n")
    print("=" * 60)

    event = initial_state
    seen = set()
    events = []
    started_at = time.time()
    run_id = initial_state.get("_run_id")
    config = graph_config(thread_id)
    for event in graph.stream(initial_state, config=config, stream_mode="values"):
        for key, label in [
            ("rag_result", "RAG Agent"),
            ("web_result", "Web Agent"),
            ("model_result", "Model Agent"),
            ("_merged", "Evidence Merge"),
            ("_arbitration", "Arbitration"),
            ("final_answer", "Synthesis"),
            ("_verified_answer", "FactCheck"),
            ("_deep_research", "L4 Deep Research"),
        ]:
            value = event.get(key)
            if value and key not in seen:
                seen.add(key)
                trace_event = event_from_state_key(
                    key,
                    value,
                    run_id=run_id,
                    thread_id=thread_id,
                    started_at=started_at,
                )
                if trace_event:
                    events.append(trace_event)
                    if stream_events:
                        print(json.dumps(trace_event.to_dict(), ensure_ascii=False))
                    else:
                        print(f"[done] {label} ({len(str(value))} chars)")

    print("=" * 60)
    return event, events


def main() -> None:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="Conflux multi-source research CLI")
    parser.add_argument("query", nargs="?", help="Research question")
    parser.add_argument("--index", help="Index a document directory")
    parser.add_argument("--query", dest="query_opt", help="Research question used with --index")
    parser.add_argument("--mode", choices=["phase1", "phase2"], default="phase2", help="Run mode")
    parser.add_argument("--output-dir", default="reports", help="Markdown/HTML output directory")
    parser.add_argument("--thread-id", help="LangGraph checkpoint thread id")
    parser.add_argument("--resume", help="Resume a checkpoint thread id")
    parser.add_argument("--checkpoint-backend", default="none", choices=["none", "memory"], help="Checkpoint backend")
    parser.add_argument("--stream-events", action="store_true", help="Print structured trace events as JSON lines")
    parser.add_argument("--trace-dir", help="Directory for .trace.jsonl and .summary.json outputs")

    args = parser.parse_args()
    actual_query = args.query or args.query_opt

    if args.index:
        index_command(args.index)

    if actual_query:
        query_command(
            actual_query,
            mode=args.mode,
            output_dir=args.output_dir,
            thread_id=args.thread_id,
            resume=args.resume,
            checkpoint_backend=args.checkpoint_backend,
            stream_events=args.stream_events,
            trace_dir=args.trace_dir,
        )
    elif not args.index:
        parser.print_help()
        print("\nExamples:")
        print("  python -m conflux --index data/documents/")
        print('  python -m conflux "How should RAG/Web/Model arbitration work?" --stream-events')


if __name__ == "__main__":
    main()
