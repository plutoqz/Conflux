"""CLI 入口 — $ python -m conflux "你的问题"

用法：
  python -m conflux "量子计算对密码学的威胁是什么？"
  python -m conflux --index data/documents/  # 先建索引
  python -m conflux --index data/documents/ --query "你的问题"
"""

import argparse
import sys
from pathlib import Path

from langchain_core.documents import Document

from .config import load as load_config
from .model_factory import create_chat_model, create_embedding_model, validate_embedding_credentials, validate_runtime_credentials
from .rag import (
    chunk_documents,
    clear_index,
    create_vector_store,
    index_documents,
    HybridRetriever,
)
from .tools import ask_model, create_rag_tool, search_web, set_model
from .agent import ResearchAgent, create_sub_agent
from .graph import create_graph
from .graph_v2 import create_multi_agent_graph
from .report import write_report_artifacts


def _configure_console_encoding() -> None:
    """Windows 控制台默认 GBK 时，避免 Unicode 报告打印崩溃。"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def index_command(docs_dir: str):
    """索引文档目录中的所有文件"""
    load_config()
    credential_problems = validate_embedding_credentials()
    if credential_problems:
        print("错误：构建 RAG 索引缺少必要 embedding 凭据：")
        for problem in credential_problems:
            print(f"- {problem}")
        print("\n本项目默认 API-first，Embedding 通过远程 API 调用。请配置 OPENAI_API_KEY，")
        print("或使用 CONFLUX_EMBEDDING__API_KEY 覆盖。")
        sys.exit(2)

    doc_path = Path(docs_dir)
    if not doc_path.exists():
        print(f"错误：目录不存在 — {doc_path}")
        sys.exit(1)

    files = list(doc_path.glob("*"))
    txt_files = [f for f in files if f.suffix in (".txt", ".md")]
    if not txt_files:
        print(f"警告：{doc_path} 下没有找到 .txt / .md 文件")
        return

    documents = []
    for fp in txt_files:
        text = fp.read_text(encoding="utf-8")
        documents.append(Document(
            page_content=text,
            metadata={"source": str(fp.name)},
        ))

    print(f"读取 {len(documents)} 个文档...")

    # 分块
    parents, children = chunk_documents(documents)
    print(f"分块完成：{len(parents)} 个父块，{len(children)} 个子块")

    # 索引入 ChromaDB（用子块做检索粒度）
    vector_store = create_vector_store()
    clear_index(vector_store)
    n = index_documents(vector_store, children)
    print(f"索引完成：{n} 个子块已写入向量存储")


def _empty_multi_agent_state(query: str) -> dict:
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
        "final_answer": "",
    }


def query_command(query: str, mode: str = "phase2", output_dir: str = "reports"):
    """执行一次查询"""
    load_config()

    credential_problems = validate_runtime_credentials()
    if credential_problems:
        print("错误：真实运行缺少必要凭据：")
        for problem in credential_problems:
            print(f"- {problem}")
        print("\n本项目默认 API-first，不要求本地模型。请配置远程模型/Embedding API key，例如 OPENAI_API_KEY，")
        print("或使用 CONFLUX_MODELS__REASONING__API_KEY、CONFLUX_EMBEDDING__API_KEY 等覆盖。")
        sys.exit(2)

    # 1. 创建模型
    print("→ 初始化模型...")
    reasoning_model = create_chat_model("reasoning")
    cheap_model = create_chat_model("cheap")
    set_model(reasoning_model)

    # 2. 创建检索器 + 工具
    vector_store = create_vector_store()
    retriever = HybridRetriever(vector_store)
    rag_tool = create_rag_tool(retriever)

    print(f"→ 运行模式：{mode}")

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
        final_state = _run_phase1_graph(graph, initial_state, query)
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
        )
        final_state = _run_phase2_graph(graph, _empty_multi_agent_state(query), query)

    answer = final_state.get("final_answer", "")
    if answer:
        print(f"\n{answer}\n")
        artifacts = write_report_artifacts(query, final_state, output_dir=output_dir)
        print(f"Markdown 报告：{artifacts.markdown_path.resolve()}")
        print(f"HTML 报告：{artifacts.html_path.resolve()}")
    else:
        print("\n⚠ 未能生成最终回答。请检查 API key、远程模型 API、Embedding API 和工具配置。\n")


def _run_phase1_graph(graph, initial_state: dict, query: str) -> dict:
    """运行 Phase 1 单 Agent 图。"""
    print(f"→ 开始单 Agent 调研：{query}\n")
    print("=" * 60)

    event = initial_state
    step = 0
    for event in graph.stream(initial_state, stream_mode="values"):
        step += 1
        msgs = event.get("messages", [])
        if msgs:
            last_msg = msgs[-1]
            prefix = f"[Step {step}]"
            msg_type = type(last_msg).__name__
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    print(f"{prefix} 调用工具：{tc['name']}({tc['args']})")
            elif hasattr(last_msg, "content") and last_msg.content:
                content = last_msg.content
                if isinstance(content, str) and len(content) > 200:
                    content = content[:200] + "..."
                print(f"{prefix} {msg_type}: {content}")

    print("=" * 60)
    return event


def _run_phase2_graph(graph, initial_state: dict, query: str) -> dict:
    """运行 Phase 2 三源多智能体图。"""
    print(f"→ 开始三源多智能体调研：{query}\n")
    print("=" * 60)

    event = initial_state
    seen = set()
    for event in graph.stream(initial_state, stream_mode="values"):
        for key, label in [
            ("rag_result", "RAG Agent"),
            ("web_result", "Web Agent"),
            ("model_result", "Model Agent"),
            ("_merged", "证据合并"),
            ("_arbitration", "三源仲裁"),
            ("final_answer", "报告合成"),
            ("_verified_answer", "FactCheck"),
            ("_deep_research", "L4 深化研究"),
        ]:
            value = event.get(key)
            if value and key not in seen:
                seen.add(key)
                print(f"[完成] {label} ({len(str(value))} 字符)")

    print("=" * 60)
    return event


def main():
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="Conflux — 三源知识多智能体调研系统")
    parser.add_argument("query", nargs="?", help="调研问题")
    parser.add_argument("--index", help="索引文档目录")
    parser.add_argument("--query", dest="query_opt", help="调研问题（与 --index 一起用时）")
    parser.add_argument("--mode", choices=["phase1", "phase2"], default="phase2", help="运行模式，默认 phase2 三源多智能体")
    parser.add_argument("--output-dir", default="reports", help="Markdown/HTML 报告输出目录")

    args = parser.parse_args()

    # 处理查询
    actual_query = args.query or args.query_opt

    if args.index:
        index_command(args.index)

    if actual_query:
        query_command(actual_query, mode=args.mode, output_dir=args.output_dir)
    elif not args.index:
        parser.print_help()
        print("\n示例：")
        print('  python -m conflux --index data/documents/')
        print('  python -m conflux "量子计算对密码学有什么影响？"')


if __name__ == "__main__":
    main()
