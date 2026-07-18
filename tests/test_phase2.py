"""Phase 2 多智能体主流程与报告导出测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.messages import AIMessage
from langchain_core.tools import tool


class FakeModel:
    """最小 fake chat model，避免测试触发真实 API。"""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if self.responses:
            content = self.responses.pop(0)
        else:
            content = "```final\n## 回答\n默认回答\n```"
        return AIMessage(content=content)


@tool
def fake_rag(query: str) -> str:
    """fake RAG 检索。"""
    from conflux.source_status import SourceResult

    return SourceResult(
        source="RAG",
        status="success",
        detail="fake local",
        content="RAG: Shor 算法会威胁 RSA。来源：local.txt",
    ).to_tool_text()


@tool
def fake_web(query: str) -> str:
    """fake Web 检索。"""
    from conflux.source_status import SourceResult

    return SourceResult(
        source="Web",
        status="success",
        detail="fake web",
        content="Web: NIST 已发布后量子密码标准。URL: https://example.test/nist",
    ).to_tool_text()


@tool
def fake_model_tool(query: str) -> str:
    """fake 模型知识。"""
    from conflux.source_status import SourceResult

    return SourceResult(
        source="Model",
        status="success",
        detail="fake model",
        content="Model: 量子计算主要影响公钥密码。",
    ).to_tool_text()


def test_multi_agent_graph_compiles_and_factcheck_updates_final_answer():
    from conflux.agent import create_sub_agent
    from conflux.graph_v2 import create_multi_agent_graph

    reasoning = FakeModel([
        "## 证据比较\n模型推断：RAG 与 Web 分别覆盖算法风险和标准进展。",
        "## 最终结论\n- Shor 算法威胁 RSA。[RAG]\n\n## 信息来源\nRAG/Web 可用。\n\n## 不确定性\n迁移时间仍不确定。\n\n## 证据摘要\n当前结论来自外部证据。\n\n## 工程落地建议\n制定迁移清单。",
    ])
    cheap = FakeModel([
        "仲裁：RAG 与 Web 提供不同但互补的外部证据。",
        "无法验证的声明：后量子迁移时间表未在原始来源中出现。\n整体验证结论：部分通过",
        "子问题一：迁移优先级如何确定？\n子问题二：哪些系统最先迁移？",
        "深化仲裁：新检索仍需补充独立来源。",
        "### 深化补充\n模型推断：优先处理长期保密数据和公钥基础设施。",
    ])

    rag_agent = create_sub_agent("rag", reasoning, fake_rag)
    web_agent = create_sub_agent("web", reasoning, fake_web)
    model_agent = create_sub_agent("model", reasoning, fake_model_tool)
    graph = create_multi_agent_graph(rag_agent, web_agent, model_agent, reasoning, cheap)

    state = {
        "query": "量子计算对密码学有哪些威胁？",
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
    result = graph.invoke(state)

    assert result["rag_result"]
    assert result["web_result"]
    assert result["model_result"]
    assert {"builtin.rag", "builtin.web", "builtin.model"}.issubset(result["source_results"])
    evidence_sources = set(__import__("json").loads(result["_evidence_json"])["source_statuses"])
    assert "RAG" in evidence_sources and "builtin.rag" in evidence_sources
    assert result["_arbitration"]
    assert result["_evidence_json"]
    assert result["_factcheck_status"] == "needs_review"
    assert result["_factcheck_report"]
    assert result["_deep_research"]
    assert result["_deep_queries"]
    assert result["_deep_factcheck_report"]
    assert result["_deep_evidence_json"]
    assert len(reasoning.calls) == 2  # Model Analyst once, then final synthesis once.
    assert result["_run_summary"]["slo_status"] == "pass"
    assert "deep_research" in result["_run_summary"]["stages"]


def test_evidence_merge_preserves_sources_when_arbitration_times_out():
    from conflux.graph_v2 import evidence_merge
    from conflux.source_status import SourceResult

    class TimeoutModel:
        def invoke(self, messages):
            raise TimeoutError("Request timed out")

    state = {
        "query": "示例问题",
        "rag_result": SourceResult(source="RAG", status="success", content="本地证据").to_tool_text(),
        "web_result": SourceResult(source="Web", status="success", content="网页证据").to_tool_text(),
        "model_result": SourceResult(source="Model", status="success", content="模型推断").to_tool_text(),
        "source_results": {},
        "_run_summary": {},
    }

    result = evidence_merge(state, arbitrator_model=TimeoutModel())

    assert "本地证据" in result["_merged"]
    assert "ARBITRATION_UNREVIEWED" in result["_arbitration"]
    assert result["_pipeline_stage"] == "evidence_merged"


def test_report_artifacts_include_markdown_and_html(tmp_path):
    from conflux.report import build_markdown_report, write_report_artifacts

    state = {
        "final_answer": "## 回答\n这是最终报告。",
        "_verified_answer": "验证通过：所有关键声明均有信息源支持",
        "_deep_research": "深化补充",
        "_arbitration": "仲裁：三源一致。",
        "_evidence_json": '{"total_nodes": 3}',
        "_source_statuses": {
            "RAG": {"status": "success", "detail": "test", "content": "rag"},
            "Web": {"status": "failed", "detail": "test", "error": "timeout", "content": ""},
            "Model": {"status": "success", "detail": "test", "content": "model"},
        },
        "_run_summary": {
            "mode": "phase2",
            "elapsed_ms": 123,
            "slo_p95_ms": 45000,
            "slo_status": "pass",
            "stages": ["dispatch", "synthesize"],
        },
        "_quality_report": {
            "overall": 4.2,
            "passed": True,
            "scores": {"运行过程": 4, "报告质量": 5},
            "notes": [],
        },
        "_merged": "RAG/Web/Model 原始输出",
    }

    markdown = build_markdown_report("测试问题", state)
    assert "# Conflux 调研报告" in markdown
    assert "## 最终报告" in markdown
    assert "## FactCheck 验证" in markdown
    assert "## 信息来源状态" in markdown
    assert "failed" in markdown
    assert "## L4 深化研究" in markdown
    assert "## 运行摘要" in markdown
    assert "## 质量评分" in markdown

    artifacts = write_report_artifacts("测试问题", state, output_dir=tmp_path)
    assert artifacts.markdown_path.exists()
    assert artifacts.html_path.exists()
    assert "Conflux 调研报告" in artifacts.markdown_path.read_text(encoding="utf-8")
    html = artifacts.html_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "这是最终报告" in html


def test_bm25_sparse_results_are_ranked_by_score(monkeypatch):
    from langchain_core.documents import Document

    from conflux.rag.retriever import HybridRetriever

    class FakeVectorStore:
        def similarity_search_with_score(self, query, k):
            return []

        def get(self, include=None):
            return {
                "documents": ["alpha", "target target target", "beta"],
                "metadatas": [
                    {"chunk_id": "a"},
                    {"chunk_id": "target"},
                    {"chunk_id": "b"},
                ],
            }

    retriever = HybridRetriever(FakeVectorStore())
    monkeypatch.setattr(retriever, "_tokenize", lambda text: text.split())
    def fake_get(*path, default=None):
        if path[-1] in {"top_k", "final_k"}:
            return 2
        if path[-1] == "dense_weight":
            return 0.7
        if path[-1] == "bm25_weight":
            return 0.3
        return default

    monkeypatch.setattr("conflux.rag.retriever.get", fake_get)

    docs = retriever.search("target")

    assert docs
    assert isinstance(docs[0], Document)
    assert docs[0].metadata["chunk_id"] == "target"


def test_rag_tool_marks_unrelated_hits_as_no_evidence():
    from langchain_core.documents import Document

    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class FakeRetriever:
        def search(self, query):
            return [
                Document(
                    page_content="欧盟 AI Act 风险分级和后量子密码标准。",
                    metadata={"source": "ai-regulation.txt", "chunk_id": "c1"},
                )
            ]

    result = create_rag_tool(FakeRetriever()).invoke({
        "query": "Retrieval-Augmented Multi-Agent Systems 三源仲裁"
    })
    parsed = parse_source_results(str(result))

    assert parsed
    assert parsed[-1].status == "no_evidence"


def test_rag_tool_keeps_relevant_hits_success():
    from langchain_core.documents import Document

    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class FakeRetriever:
        def search(self, query):
            return [
                Document(
                    page_content="Retrieval-Augmented Multi-Agent Systems 使用三源仲裁处理冲突。",
                    metadata={"source": "agent-rag.txt", "chunk_id": "c1"},
                )
            ]

    result = create_rag_tool(FakeRetriever()).invoke({
        "query": "Retrieval-Augmented Multi-Agent Systems 三源仲裁"
    })
    parsed = parse_source_results(str(result))

    assert parsed
    assert parsed[-1].status == "success"


def test_evidence_graph_has_structured_payload():
    from conflux.evidence import build_evidence_graph

    graph = build_evidence_graph({
        "RAG": "RSA 会受到 Shor 算法威胁。",
        "Web": "RSA 会受到 Shor 算法威胁。",
        "Model": "RSA 不会受到 Shor 算法威胁。",
    })
    payload = graph.to_dict()

    assert payload["summary"]["total_nodes"] == 3
    assert payload["summary"]["source_counts"]["RAG"] == 1
    assert "nodes" in payload
    assert payload["nodes"][0]["claim"]


def test_failed_sources_do_not_participate_in_evidence_graph():
    from conflux.evidence import build_evidence_graph_from_results
    from conflux.source_status import SourceResult

    graph = build_evidence_graph_from_results({
        "RAG": SourceResult(
            source="RAG",
            status="success",
            detail="local",
            content="Loop Engineering 强调围绕智能体循环进行系统化设计。",
        ),
        "Web": SourceResult(
            source="Web",
            status="failed",
            detail="duckduckgo",
            error="timeout",
            content="搜索失败后模型补写的内容不能算 Web 来源。",
        ),
        "Model": SourceResult(
            source="Model",
            status="success",
            detail="llm",
            content="Loop Engineering 关注触发器、反馈和评估闭环。",
        ),
    })
    payload = graph.to_dict()

    assert payload["source_statuses"]["Web"]["status"] == "failed"
    assert payload["summary"]["source_counts"].get("Web") is None
    assert all(node["source"] != "Web" for node in payload["nodes"])


def test_low_relevance_sources_enter_graph_with_reduced_weight():
    from conflux.evidence import build_evidence_graph_from_results
    from conflux.source_status import AgentClaim, SourceResult

    graph = build_evidence_graph_from_results({
        "RAG": SourceResult(
            source="RAG",
            status="low_relevance",
            detail="local",
            content="GIS systems can use geospatial analysis context.",
            claims=[
                AgentClaim(
                    claim="GIS systems can use geospatial analysis context.",
                    source="RAG",
                    evidence_refs=["[RAG:gis#chunk-001]"],
                    confidence=0.8,
                )
            ],
        ),
        "Web": SourceResult(
            source="Web",
            status="no_evidence",
            detail="web",
            content="Search returned unrelated pages.",
        ),
        "Model": SourceResult(
            source="Model",
            status="success",
            detail="model",
            content="Model context.",
        ),
    })
    payload = graph.to_dict()

    rag_nodes = [node for node in payload["nodes"] if node["source"] == "RAG"]
    assert rag_nodes
    assert rag_nodes[0]["authority_score"] < 0.7
    assert rag_nodes[0]["confidence"] < 0.8
    assert "low relevance" in " ".join(rag_nodes[0]["limitations"])
    assert all(node["source"] != "Web" for node in payload["nodes"])


def test_phase2_marks_failed_web_as_failed_not_consensus():
    from conflux.agent import create_sub_agent
    from conflux.graph_v2 import create_multi_agent_graph
    from conflux.source_status import SourceResult

    @tool
    def ok_rag(query: str) -> str:
        """fake successful RAG."""
        return SourceResult(
            source="RAG",
            status="success",
            detail="fake local",
            content="RAG: Loop Engineering 使用循环、反馈和验证来改进智能体流程。",
        ).to_tool_text()

    @tool
    def failed_web(query: str) -> str:
        """fake failed Web."""
        return SourceResult(
            source="Web",
            status="failed",
            detail="fake web",
            error="timeout",
            content="Web 搜索失败。",
        ).to_tool_text()

    @tool
    def ok_model(query: str) -> str:
        """fake successful model."""
        return SourceResult(
            source="Model",
            status="success",
            detail="fake model",
            content="Model: Loop Engineering 可用于设计触发、执行、评估和改进闭环。",
        ).to_tool_text()

    reasoning = FakeModel([
        "## 证据分析\n模型推断：RAG 支持反馈闭环，Web 检索失败。",
        "## 最终结论\n- Loop Engineering 关注反馈闭环。[RAG][Model]\n\n## 信息来源\nWeb failed。\n\n## 不确定性\nWeb 失败，仍需外部检索。\n\n## 证据摘要\nRAG 与 Model 有部分一致。\n\n## 工程落地建议\n建立状态标注。",
    ])
    cheap = FakeModel([
        "仲裁：RAG 与 Model 可投票，Web failed 不参与。",
        "验证通过：所有关键声明均有信息源支持",
        "如何补齐 Web 权威来源？",
        "深化仲裁：RAG 有证据，Web 仍失败。",
        "### 深化补充\n证据支持：当前只验证了 RAG 与 Model，Web 需重试。",
    ])

    graph = create_multi_agent_graph(
        create_sub_agent("rag", reasoning, ok_rag),
        create_sub_agent("web", reasoning, failed_web),
        create_sub_agent("model", reasoning, ok_model),
        reasoning,
        cheap,
    )

    result = graph.invoke({
        "query": "研究 Loop Engineering 的工程闭环",
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
    })

    import json

    evidence_payload = json.loads(result["_evidence_json"])

    assert result["_source_statuses"]["Web"]["status"] == "failed"
    assert evidence_payload["source_statuses"]["Web"]["status"] == "failed"
    assert all(node["source"] != "Web" for node in evidence_payload["nodes"])
    assert result["_quality_report"]["scores"]["证据图结构"] >= 4
    assert "Web failed" in result["final_answer"] or "Web 失败" in result["final_answer"]
