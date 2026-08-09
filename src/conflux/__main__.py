"""CLI entrypoint for Conflux."""

from __future__ import annotations

import argparse
import functools
import json
import sys
import time
from pathlib import Path
from typing import Callable

from langchain_core.documents import Document

from .agent import create_sub_agent
from .checkpointing import create_checkpointer, graph_config
from .config import get as config_get
from .config import load as load_config
from .config import override as config_override
from .core.storage_cli import doctor_command, import_legacy_command, init_command, migrate_command
from .core.contracts import RunContext
from .core.runtime_home import database_path
from .graph_v2 import create_v2_research_graph
from .model_factory import (
    create_research_models,
    validate_embedding_credentials,
    validate_runtime_credentials,
)
from .query_planner import QueryRewriteProvider
from .rag import HybridRetriever, SemanticReranker, chunk_documents, clear_index, create_vector_store, index_documents
from .replay import build_replay_components, load_replay_bundle
from .research_modes import resolve_research_profile
from .tools import create_rag_tool, create_web_tool, set_model
from .trace import (
    event_from_state_key,
    events_from_source_results,
    new_run_id,
    TraceEvent,
    write_run_summary,
    write_trace_jsonl,
)


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


def _new_v2_state(
    query: str,
    *,
    deadline_at: float | None = None,
    run_id: str | None = None,
    depth: str = "standard",
    timeout_seconds: int | None = None,
    baseline_variant: str = "B4",
) -> dict:
    """Create initial state for the V2 answer_first pipeline."""
    from .graph_v2 import _new_state

    return _new_state(
        query,
        deadline_at=deadline_at,
        run_id=run_id,
        depth=depth,
        timeout_seconds=timeout_seconds,
        baseline_variant=baseline_variant,
    )


def _with_run_context_config(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        run_context = kwargs.get("run_context")
        values = run_context.config_overrides if run_context is not None else None
        with config_override(values):
            return func(*args, **kwargs)

    return wrapped


@_with_run_context_config
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
    depth: str | None = None,
    started_at: float | None = None,
    deadline_at: float | None = None,
    commit_reserve_seconds: float | None = None,
    replay: str | None = None,
    baseline_variant: str = "B4",
    run_context: RunContext | None = None,
    ledger_db_path: str | Path | None = None,
    on_graph_state: Callable[[dict, list], None] | None = None,
    should_stop: Callable[[], None] | None = None,
) -> dict:
    """Run one research query."""

    loaded_config = load_config()
    research_profile = resolve_research_profile(depth)
    started_at = float(started_at or time.time())
    deadline_at = float(deadline_at or (started_at + research_profile.timeout_seconds))
    commit_reserve_seconds = float(
        research_profile.commit_reserve_seconds
        if commit_reserve_seconds is None
        else max(0.0, commit_reserve_seconds)
    )
    if run_context is not None:
        run_id = run_context.run_id
        thread_id = run_context.thread_id or thread_id
    run_id = run_id or new_run_id()
    research_config = loaded_config.get("research", {}) or {}
    pipeline = str(research_config.get("pipeline") or "answer_first").casefold()
    if pipeline != "answer_first":
        # P1/P1.5 pipelines were removed (plan stage K); normalize to V2.
        print(f"-> Warning: research.pipeline '{pipeline}' is no longer supported; using answer_first.")
        pipeline = "answer_first"
    replay_bundle = load_replay_bundle(replay) if replay else None
    baseline_variant = str(baseline_variant or "B4").upper()
    if replay_bundle:
        bundle_query = str(replay_bundle.get("query") or "").strip()
        if bundle_query and bundle_query != query:
            raise ValueError("replay bundle query does not match the requested query")
        for key, expected in (
            ("prompt_version", "research-prompts-v3"),
            ("model_config_version", "research-model-profile-v1"),
        ):
            if replay_bundle.get(key) != expected:
                raise ValueError(f"replay bundle {key} does not match the current V2 configuration")
        run_id = str(replay_bundle.get("run_id") or run_id)
        role_models, rag_tool, web_tool = build_replay_components(replay_bundle)
        model_trace = None
        vector_store = None
        retriever = None
        v2_rewriter = None
        v2_semantic_reranker = None
        print(f"-> Replay bundle: {Path(replay).resolve()}")
    else:
        credential_problems = validate_runtime_credentials(
            research_profile.depth,
            include_legacy_presets=False,
        )
        if credential_problems:
            print("Error: real API execution is missing required credentials.")
            for problem in credential_problems:
                print(f"- {problem}")
            print("\nConfigure OPENAI_API_KEY, or source-specific CONFLUX_* API key overrides.")
            sys.exit(2)

        vector_store = create_vector_store()
        retriever = HybridRetriever(vector_store)
        print("-> Initializing models...")
        role_models, model_trace = create_research_models(
            research_profile.depth,
            deadline_at=deadline_at,
            commit_reserve_seconds=commit_reserve_seconds,
        )
        set_model(role_models["analyst"])
        v2_rewriter = QueryRewriteProvider(role_models["verifier"])
        # R1 消融结论：LLM judge rerank 默认关闭；graph 按 llm_rerank_enabled
        # 开关决定是否创建 SemanticReranker。
        v2_semantic_reranker = None
        rag_tool = create_rag_tool(
            retriever,
            v2_rewriter,
            v2_semantic_reranker,
            research_profile,
        )
        web_tool = create_web_tool(
            research_profile,
            run_id=run_id,
            query_rewriter=v2_rewriter,
            deadline_at=deadline_at,
            commit_reserve_seconds=commit_reserve_seconds,
        )

    effective_thread_id = resume or thread_id or run_id
    checkpoint = create_checkpointer(checkpoint_backend)
    print(f"-> Mode: {mode}")
    print(f"-> Research pipeline: {pipeline}")
    print(f"-> Research depth: {research_profile.depth}")
    print(f"-> Baseline variant: {baseline_variant}")
    if replay_bundle:
        print("-> Execution mode: fixed replay")
    if model_trace:
        for role, identity in model_trace.get("roles", {}).items():
            print(f"-> Model {role}: {identity.get('model')} ({identity.get('preset')})")
    print(f"-> Run id: {run_id}")
    print(f"-> Thread id: {effective_thread_id}")
    print(f"-> Checkpoint backend: {checkpoint.backend}")

    # V2 answer_first pipeline — simplified 4-step flow
    if replay_bundle:
        rag_agent = rag_tool
        web_agent = web_tool
    else:
        retriever = HybridRetriever(vector_store)
        rag_agent = create_sub_agent("rag", role_models["reranker"], rag_tool)
        web_agent = create_sub_agent("web", role_models["reranker"], web_tool)
    graph = create_v2_research_graph(
        rag_agent,
        web_agent,
        planner_model=role_models["planner"],
        synthesizer_model=role_models["synthesizer"],
        independent_model=role_models["analyst"],
        arbitration_model=role_models["planner"],
        verifier_model=role_models["verifier"],
        profile=research_profile,
        retriever=retriever,
        query_rewriter=v2_rewriter,
        semantic_reranker=v2_semantic_reranker,
        reranker_model=role_models.get("reranker"),
        llm_rerank_enabled=(
            bool(config_get("research", "semantic_rerank", default=False))
            if not replay_bundle
            else False
        ),
        run_id=run_id,
        deadline_at=deadline_at,
        commit_reserve_seconds=commit_reserve_seconds,
        baseline_variant=baseline_variant,
        max_parallel_subquestions=1 if replay_bundle else None,
    )
    initial_state = _new_v2_state(
        query,
        deadline_at=deadline_at,
        run_id=run_id,
        depth=research_profile.depth,
        timeout_seconds=research_profile.timeout_seconds,
        baseline_variant=baseline_variant,
    )
    final_state, trace_events = _run_phase2_graph(
        graph,
        initial_state,
        query,
        stream_events=stream_events,
        thread_id=effective_thread_id,
        on_state=on_graph_state,
        should_stop=should_stop,
    )

    # V2: 报告已在管道内完成组装
    answer = final_state.get("_report_markdown") or final_state.get("final_answer") or ""
    artifacts = None
    if answer:
        print(f"\n{answer[:3000]}\n")
        from .report import write_v2_report_artifacts
        artifacts = write_v2_report_artifacts(query, final_state, output_dir)
        confidence = final_state.get("_confidence", "unverified")
        confidence_label = {"high": "高可信", "medium": "中可信", "low": "低可信", "unverified": "未核验"}.get(confidence, confidence)
        print(f"Report Markdown: {artifacts.markdown_path.resolve()}")
        print(f"Report HTML: {artifacts.html_path.resolve()}")
        print(f"可信度：{confidence_label}")
    else:
        print("\nWarning: no final answer was generated. Check API, embedding, and tool configuration.\n")

    trace_root = Path(trace_dir or output_dir)
    trace_path = trace_root / f"{run_id}.trace.jsonl"
    summary_path = trace_root / f"{run_id}.summary.json"
    write_trace_jsonl(trace_events, trace_path)
    summary = dict(final_state.get("_run_summary") or {})
    # V2 summary
    summary.update({
            "delivery_status": final_state.get("_delivery_status", "diagnostic_only"),
            "delivery_assessment": final_state.get("_delivery_assessment") or {},
            "report_md_path": str(artifacts.markdown_path.resolve()) if artifacts and artifacts.markdown_path else "",
            "report_html_path": str(artifacts.html_path.resolve()) if artifacts and artifacts.html_path else "",
            "report_evidence_path": str(artifacts.evidence_json_path.resolve()) if artifacts and artifacts.evidence_json_path else "",
            "report_sources_path": str(artifacts.raw_sources_path.resolve()) if artifacts and artifacts.raw_sources_path else "",
            "report_deep_evidence_path": "",
            "report_audit_path": str(artifacts.audit_markdown_path.resolve()) if artifacts and artifacts.audit_markdown_path else "",
            "diagnostic_markdown_path": "",
            "diagnostic_html_path": "",
            "diagnostic_evidence_path": "",
            "diagnostic_sources_path": "",
            "diagnostic_deep_evidence_path": "",
            "diagnostic_audit_path": "",
            "run_id": run_id,
            "thread_id": effective_thread_id,
            "query": query,
            "final_answer": answer[:2000] if answer else "",
            "checkpoint_backend": checkpoint.backend,
            "resumed": bool(resume),
            "trace_path": str(trace_path),
            "run_status": final_state.get("_run_status"),
            "report_available": bool(final_state.get("_report_available")),
             "confidence": final_state.get("_confidence"),
             "source_statuses": final_state.get("_source_statuses") or {},
             "factcheck_status": final_state.get("_factcheck_status") or "",
             "quality": final_state.get("_audit_metrics") or {},
             "budget_consumed": final_state.get("_budget_state") or {},
             "degradation_reason": (final_state.get("_budget_state") or {}).get("degradation_reasons") or [],
             "dropped_reason": (final_state.get("_budget_state") or {}).get("dropped_reasons") or [],
             "replay_mode": bool(replay_bundle),
             "replay_bundle": str(Path(replay).resolve()) if replay else "",
             "baseline_variant": final_state.get("_baseline_variant") or baseline_variant,
             "baseline_policy": final_state.get("_baseline_policy") or {},
         })
    final_state["_report_artifacts"] = {
        "markdown_path": summary["report_md_path"],
        "html_path": summary["report_html_path"],
        "evidence_json_path": summary["report_evidence_path"],
        "raw_sources_path": summary["report_sources_path"],
        "deep_evidence_json_path": summary["report_deep_evidence_path"],
        "audit_markdown_path": summary["report_audit_path"],
        "diagnostic_markdown_path": summary["diagnostic_markdown_path"],
        "diagnostic_html_path": summary["diagnostic_html_path"],
        "diagnostic_evidence_path": summary["diagnostic_evidence_path"],
        "diagnostic_sources_path": summary["diagnostic_sources_path"],
        "diagnostic_deep_evidence_path": summary["diagnostic_deep_evidence_path"],
        "diagnostic_audit_path": summary["diagnostic_audit_path"],
    }
    if ledger_db_path is not None:
        from .adapters.evidence_ledger_store import persist_final_state

        ledger_artifacts = [
            {
                "id": f"{run_id}:{key}",
                "type": "report" if "report" in key else "artifact",
                "location": value,
            }
            for key, value in final_state["_report_artifacts"].items()
            if value
        ]
        try:
            ledger_result = persist_final_state(
                final_state,
                db_path=ledger_db_path,
                artifacts=ledger_artifacts,
            )
        except Exception as exc:
            ledger_result = {
                "persisted": False,
                "reason": "ledger_persistence_failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
        final_state["_ledger_persistence"] = ledger_result
        summary["evidence_ledger"] = ledger_result
    write_run_summary(summary, summary_path)
    print(f"Trace JSONL: {trace_path.resolve()}")
    print(f"Run summary: {summary_path.resolve()}")

    return final_state


def _run_phase2_graph(
    graph,
    initial_state: dict,
    query: str,
    *,
    stream_events: bool = False,
    thread_id: str | None = None,
    on_state: Callable[[dict, list], None] | None = None,
    should_stop: Callable[[], None] | None = None,
) -> tuple[dict, list]:
    print(f"-> Starting three-source multi-agent research: {query}\n")
    print("=" * 60)

    event = initial_state
    seen = set()
    events = []
    started_at = time.time()
    run_id = initial_state.get("_run_id")
    config = graph_config(thread_id)
    if should_stop:
        should_stop()
    for event in graph.stream(initial_state, config=config, stream_mode="values"):
        for key, label in [
            ("source_results", "Dynamic sources"),
            ("_research_plan", "Research Plan"),
            ("rag_result", "RAG Agent"),
            ("web_result", "Web Agent"),
            ("model_result", "Model Agent"),
            ("_merged", "Evidence Merge"),
            ("_arbitration", "Arbitration"),
            ("final_answer", "Synthesis"),
            ("_verified_answer", "FactCheck"),
            ("_factcheck_report", "Verify & Revise"),
            ("_verification_issues", "Verify & Revise"),
            ("_deep_queries", "Gap Research"),
            ("_deep_research", "L4 Deep Research"),
        ]:
            value = event.get(key)
            if value and key not in seen:
                seen.add(key)
                if key == "source_results":
                    dynamic_events = events_from_source_results(
                        value,
                        run_id=run_id,
                        thread_id=thread_id,
                        started_at=started_at,
                    )
                    events.extend(dynamic_events)
                    for dynamic_event in dynamic_events:
                        if stream_events:
                            print(json.dumps(dynamic_event.to_dict(), ensure_ascii=False))
                    if not stream_events and dynamic_events:
                        print(f"[done] {label} ({len(dynamic_events)} sources)")
                    continue
                trace_event = event_from_state_key(
                    key, value, run_id=run_id, thread_id=thread_id, started_at=started_at
                )
                if trace_event:
                    if key == "final_answer" and event.get("_synthesis_status"):
                        trace_event.status = str(event["_synthesis_status"])
                        trace_event.metadata["synthesis_error"] = str(event.get("_synthesis_error") or "")
                    events.append(trace_event)
                    if stream_events:
                        print(json.dumps(trace_event.to_dict(), ensure_ascii=False))
                    else:
                        print(f"[done] {label} ({len(str(value))} chars)")
        if on_state:
            on_state(event, events)
        if should_stop:
            should_stop()

    budget = event.get("_budget_state") or {}
    observability_event = TraceEvent(
        stage="v2_run_summary",
        status=str(event.get("_run_status") or "failed"),
        elapsed_ms=float(event.get("_elapsed_ms") or 0.0),
        run_id=run_id,
        thread_id=thread_id,
        summary="V2 query plan, evidence, verification and budget summary",
        metadata={
            "query_plan": event.get("_sub_questions") or [],
            "provider_trace": {
                key: value.get("provider_trace", [])
                for key, value in (event.get("_source_statuses") or {}).items()
                if isinstance(value, dict)
            },
            "candidate_evidence": event.get("_round0_results") or {},
            "dropped_reason": budget.get("dropped_reasons") or [],
            "claim_ids": [
                item.get("claim_id")
                for item in event.get("_claim_records") or []
                if isinstance(item, dict)
            ],
            "verification_result": event.get("_model_verification") or {},
            "conflict_search": event.get("_model_arbitration") or {},
            "budget_consumed": budget,
            "degradation_reason": budget.get("degradation_reasons") or [],
            "prompt_version": "research-prompts-v3",
            "model_config_version": "research-model-profile-v1",
        },
    )
    events.append(observability_event)
    if on_state:
        on_state(event, events)
    if stream_events:
        print(json.dumps(observability_event.to_dict(), ensure_ascii=False))

    print("=" * 60)
    return event, events


# ── plugin CLI ──────────────────────────────────────────────────────

def _plugin_command(args: argparse.Namespace) -> None:
    """Handle ``conflux plugin <action>``."""
    import os
    from .core.registry import get_registry, reset_registry
    from .adapters.plugin_loader import load_builtin_plugins, load_plugins_from_dirs
    from .sdk.manifest import load_manifest, validate_manifest

    registry = get_registry()
    load_builtin_plugins(registry)

    # Load user plugin dirs from --plugin-dir and CONFLUX_PLUGIN_DIRS.
    plugin_dirs = list(getattr(args, "plugin_dirs", []) or [])
    env_dirs = os.environ.get("CONFLUX_PLUGIN_DIRS", "")
    if env_dirs:
        plugin_dirs.extend(p.strip() for p in env_dirs.split(os.pathsep) if p.strip())
    if plugin_dirs:
        load_plugins_from_dirs(plugin_dirs, registry)

    if args.plugin_action == "list":
        plugins = registry.list_plugins()
        if not plugins:
            print("No plugins registered.")
            return
        for p in plugins:
            caps = p.capabilities
            print(f"{p.id} v{p.manifest.version} — {len(caps)} capabilities")
            if getattr(args, "verbose", False):
                for cap in caps:
                    print(f"  - {cap.id}: {cap.description or '(no description)'}")

    elif args.plugin_action == "validate":
        path = args.path
        try:
            manifest = load_manifest(path)
            issues = validate_manifest(manifest)
            if issues:
                print(f"Validation issues in {path}:")
                for i in issues:
                    print(f"  - {i}")
            else:
                print(f"Manifest {path} is valid.")
                print(f"  Plugin: {manifest.id} v{manifest.version}")
                print(f"  Capabilities: {len(manifest.capabilities)}")
                for cap in manifest.capabilities:
                    print(f"    - {cap.id} [{cap.mode.value}]")
        except Exception as e:
            print(f"Error loading {path}: {e}")
            raise SystemExit(1)

    elif args.plugin_action == "inspect":
        record = registry.get(args.plugin_id)
        if record is None:
            print(f"Plugin '{args.plugin_id}' not found.")
            raise SystemExit(1)
        m = record.manifest
        print(f"Plugin: {m.id}")
        print(f"Version: {m.version}")
        print(f"Entrypoint: {m.entrypoint}")
        print(f"SDK compat: {m.sdk_compat}")
        print(f"Permissions: {[p.value for p in m.permissions]}")
        print(f"Side effects: {m.side_effects}")
        print(f"Capabilities ({len(m.capabilities)}):")
        for cap in m.capabilities:
            print(f"  - {cap.id} [{cap.mode.value}]: {cap.description}")

    else:
        print("Usage: python -m conflux plugin {list|validate|inspect} [...]")


def _workflow_command(args: argparse.Namespace) -> None:
    """Handle ``conflux workflow <action>``."""
    import os
    from .core.registry import get_registry
    from .core.policy import check_workflow_steps, validate_workflow_inputs
    from .adapters.plugin_loader import load_builtin_plugins, load_plugins_from_dirs
    from .sdk.manifest import load_workflow

    registry = get_registry()
    load_builtin_plugins(registry)

    # Load user plugins if --plugin-dir given.
    plugin_dirs = list(getattr(args, "wf_plugin_dirs", []) or [])
    env_dirs = os.environ.get("CONFLUX_PLUGIN_DIRS", "")
    if env_dirs:
        plugin_dirs.extend(p.strip() for p in env_dirs.split(os.pathsep) if p.strip())
    if plugin_dirs:
        load_plugins_from_dirs(plugin_dirs, registry)

    if args.workflow_action in {"validate", "run"}:
        path = args.path
        try:
            wf = load_workflow(path)
        except Exception as e:
            print(f"Error loading workflow {path}: {e}")
            raise SystemExit(1)

        if args.workflow_action == "run":
            from .core.workflow_compiler import execute_workflow
            from .core.contracts import StepStatus

            try:
                input_values = json.loads(args.input_json or "{}")
                if not isinstance(input_values, dict):
                    raise ValueError("--input-json must contain a JSON object")
                results = execute_workflow(wf, registry, input_values)
            except Exception as exc:
                print(f"Workflow execution failed: {exc}")
                raise SystemExit(1)
            for step_id, result in results.items():
                print(f"{step_id}: {result.status.value}")
                if result.error:
                    print(f"  error: {result.error}")
            if any(result.status != StepStatus.SUCCESS for result in results.values()):
                raise SystemExit(1)
        elif getattr(args, "dry_run", False):
            from .core.workflow_compiler import dry_run_workflow, workflow_text_graph
            print(workflow_text_graph(wf))
            print()
            print(dry_run_workflow(wf, registry))
        else:
            from .core.workflow_compiler import compile_workflow
            result = compile_workflow(wf, registry)
            print(f"Workflow: {wf.id} v{wf.version}")
            print(f"Steps: {len(wf.steps)}")
            if result.issues:
                print(f"\nIssues ({len(result.issues)}):")
                for i in result.issues:
                    print(f"  {i}")
            if result.is_valid:
                print("\nWorkflow is valid.")
            else:
                print("\nWorkflow is INVALID.")
                raise SystemExit(1)
    else:
        print("Usage: python -m conflux workflow {validate|run} <path> [options]")


def main() -> None:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="Conflux multi-source research CLI")
    sub = parser.add_subparsers(dest="command", help="Subcommands")

    # ── plugin subcommands ──────────────────────────────────────
    plugin_parser = sub.add_parser("plugin", help="Plugin management")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_action")

    list_parser = plugin_sub.add_parser("list", help="List registered plugins")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show capability details")
    list_parser.add_argument("--plugin-dir", action="append", default=[], dest="plugin_dirs",
                             help="Extra plugin directory (repeatable); also read from CONFLUX_PLUGIN_DIRS env var")

    validate_parser = plugin_sub.add_parser("validate", help="Validate a plugin manifest")
    validate_parser.add_argument("path", help="Path to manifest.yaml or plugin directory")

    inspect_parser = plugin_sub.add_parser("inspect", help="Show plugin details")
    inspect_parser.add_argument("plugin_id", help="Plugin id to inspect")
    inspect_parser.add_argument("--plugin-dir", action="append", default=[], dest="plugin_dirs",
                                help="Extra plugin directory for resolving the plugin")

    # ── workflow subcommands ────────────────────────────────────
    wf_parser = sub.add_parser("workflow", help="Workflow management")
    wf_sub = wf_parser.add_subparsers(dest="workflow_action")

    wf_validate_parser = wf_sub.add_parser("validate", help="Validate a workflow definition")
    wf_validate_parser.add_argument("path", help="Path to workflow YAML file")
    wf_validate_parser.add_argument("--dry-run", action="store_true", help="Show execution plan without running")
    wf_validate_parser.add_argument("--plugin-dir", action="append", default=[], dest="wf_plugin_dirs",
                                     help="Extra plugin directory for resolving capabilities")
    wf_run_parser = wf_sub.add_parser("run", help="Run a workflow with JSON inputs")
    wf_run_parser.add_argument("path", help="Path to workflow YAML file")
    wf_run_parser.add_argument("--input-json", default="{}", help="Workflow inputs as a JSON object")
    wf_run_parser.add_argument("--plugin-dir", action="append", default=[], dest="wf_plugin_dirs",
                               help="Extra plugin directory for resolving capabilities")

    # ── M3 runtime storage subcommands ─────────────────────────
    init_parser = sub.add_parser("init", help="Initialize the Conflux runtime home")
    init_parser.add_argument("--home", help="Runtime home path (default: CONFLUX_HOME or platform default)")
    init_parser.add_argument("--mode", choices=["local"], default="local")

    migrate_parser = sub.add_parser("migrate", help="Apply runtime schema migrations")
    migrate_parser.add_argument("--home", help="Runtime home path")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Preview pending migrations")

    doctor_parser = sub.add_parser("doctor", help="Diagnose runtime home and configuration")
    doctor_parser.add_argument("--home", help="Runtime home path")

    import_legacy_parser = sub.add_parser("import-legacy", help="Import legacy P2 JSON state")
    import_legacy_parser.add_argument("--home", help="Runtime home path")
    import_legacy_parser.add_argument("--source", required=True, help="Legacy reports/workbench/projects path")
    import_legacy_parser.add_argument("--dry-run", action="store_true", help="Count candidate JSON files only")

    # ── legacy research CLI (preserved) ─────────────────────────
    research_parser = sub.add_parser("research", help="Run a research query (default)")
    research_parser.add_argument("query_positional", nargs="?", help="Research question")
    research_parser.add_argument("--index", help="Index a document directory")
    research_parser.add_argument("--query", dest="query_opt", help="Research question used with --index")
    research_parser.add_argument("--mode", choices=["phase2"], default="phase2", help="Run mode (phase2 only)")
    research_parser.add_argument("--depth", choices=["quick", "standard", "deep", "low", "medium", "high"], default="standard", help="Research depth and model tier")
    research_parser.add_argument("--output-dir", default="reports", help="Markdown/HTML output directory")
    research_parser.add_argument("--thread-id", help="LangGraph checkpoint thread id")
    research_parser.add_argument("--resume", help="Resume a checkpoint thread id")
    research_parser.add_argument("--checkpoint-backend", default="none", choices=["none", "memory"], help="Checkpoint backend")
    research_parser.add_argument("--stream-events", action="store_true", help="Print structured trace events as JSON lines")
    research_parser.add_argument("--trace-dir", help="Directory for .trace.jsonl and .summary.json outputs")
    research_parser.add_argument("--replay", help="Run V2 from a fixed replay bundle without external APIs")
    research_parser.add_argument("--baseline-variant", choices=["B2", "B3", "B4"], default="B4")

    # ── also accept top-level args for backward compat ──────────
    parser.add_argument("query", nargs="?", help="Research question (legacy mode)")
    parser.add_argument("--index", help="Index a document directory")
    parser.add_argument("--query", dest="query_opt", help="Research question used with --index")
    parser.add_argument("--mode", choices=["phase2"], default="phase2", help="Run mode (phase2 only)")
    parser.add_argument("--depth", choices=["quick", "standard", "deep", "low", "medium", "high"], default="standard", help="Research depth and model tier")
    parser.add_argument("--output-dir", default="reports", help="Markdown/HTML output directory")
    parser.add_argument("--thread-id", help="LangGraph checkpoint thread id")
    parser.add_argument("--resume", help="Resume a checkpoint thread id")
    parser.add_argument("--checkpoint-backend", default="none", choices=["none", "memory"], help="Checkpoint backend")
    parser.add_argument("--stream-events", action="store_true", help="Print structured trace events as JSON lines")
    parser.add_argument("--trace-dir", help="Directory for .trace.jsonl and .summary.json outputs")
    parser.add_argument("--replay", help="Run V2 from a fixed replay bundle without external APIs")
    parser.add_argument("--baseline-variant", choices=["B2", "B3", "B4"], default="B4")

    args = parser.parse_args()

    if args.command == "plugin":
        _plugin_command(args)
    elif args.command == "workflow":
        _workflow_command(args)
    elif args.command == "init":
        raise SystemExit(init_command(args.home, args.mode))
    elif args.command == "migrate":
        raise SystemExit(migrate_command(args.home, args.dry_run))
    elif args.command == "doctor":
        raise SystemExit(doctor_command(args.home))
    elif args.command == "import-legacy":
        raise SystemExit(import_legacy_command(args.home, args.source, args.dry_run))
    elif args.command == "research" or (not args.command and (args.query or args.query_opt or args.index)):
        actual_query = getattr(args, "query_positional", None) or args.query or args.query_opt
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
                 depth=args.depth,
                  replay=args.replay,
                  baseline_variant=args.baseline_variant,
                  ledger_db_path=database_path(),
              )
        elif not args.index:
            parser.print_help()
            print("\nExamples:")
            print("  python -m conflux --index data/documents/")
            print('  python -m conflux "How should RAG/Web/Model arbitration work?" --stream-events')
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
