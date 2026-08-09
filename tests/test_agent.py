"""基本烟雾测试 — 验证所有模块可导入，Graph 可编译"""

import sys
from pathlib import Path
from types import SimpleNamespace

# 确保项目在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """验证核心模块可导入"""
    from conflux.config import load, get
    from conflux.model_factory import create_chat_model, create_embedding_model
    from conflux.rag import chunk_documents, create_vector_store, HybridRetriever
    from conflux.tools import create_rag_tool, search_web
    from conflux.agent import ResearchAgent, SYSTEM_PROMPT
    from conflux.graph_v2 import create_v2_research_graph
    assert True


def test_config_loads():
    """验证配置可加载"""
    from conflux.config import load, get
    cfg = load()
    assert "models" in cfg
    assert get("models", "reasoning", "provider") is not None
    assert get("embedding", "model") is not None


def test_chunking():
    """验证分块逻辑"""
    from conflux.rag import chunk_documents
    from langchain_core.documents import Document

    doc = Document(page_content="Hello " * 500, metadata={"source": "test.txt"})
    parents, children = chunk_documents([doc], parent_size=100, child_size=30)
    assert len(parents) > 0
    assert len(children) > 0
    assert all(c.metadata.get("parent_id") for c in children)


def test_index_command_uses_configured_parent_chunks(tmp_path, monkeypatch):
    from langchain_core.documents import Document
    from conflux import __main__ as cli

    captured = {}
    documents = [Document(page_content="content", metadata={"source": "doc.md"})]
    parents = [Document(page_content="parent", metadata={"chunk_id": "doc.md#p0"})]
    children = [Document(page_content="child", metadata={"chunk_id": "doc.md#p0#c0"})]

    monkeypatch.setattr(cli, "load_config", lambda: {})
    monkeypatch.setattr(cli, "validate_embedding_credentials", lambda: [])
    monkeypatch.setattr(cli, "_load_index_documents", lambda _path: documents)
    monkeypatch.setattr(
        cli,
        "config_get",
        lambda *path, default=None: {
            ("retrieval", "parent_chunk_size"): 512,
            ("retrieval", "child_chunk_size"): 128,
        }.get(path, default),
    )

    def fake_chunk(_documents, *, parent_size, child_size):
        captured["sizes"] = (parent_size, child_size)
        return parents, children

    monkeypatch.setattr(cli, "chunk_documents", fake_chunk)
    monkeypatch.setattr(cli, "create_vector_store", lambda: object())
    monkeypatch.setattr(cli, "clear_index", lambda _store: None)

    def fake_index(_store, indexed_documents):
        captured["documents"] = indexed_documents
        return len(indexed_documents)

    monkeypatch.setattr(cli, "index_documents", fake_index)

    cli.index_command(str(tmp_path))

    assert captured["sizes"] == (512, 128)
    assert captured["documents"] == parents


def test_graph_compiles():
    """验证 V2 LangGraph 可编译（不需要真实 API key）"""
    from unittest.mock import MagicMock
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool as tool_decorator

    from conflux.graph_v2 import create_v2_research_graph
    from conflux.research_modes import resolve_research_profile

    @tool_decorator
    def dummy_search(query: str) -> str:
        """Search dummy test data."""
        return f"dummy result for: {query}"

    # 用 mock 模型
    mock_model = MagicMock(spec=BaseChatModel)
    profile = resolve_research_profile("quick")
    graph = create_v2_research_graph(
        dummy_search,
        dummy_search,
        planner_model=mock_model,
        synthesizer_model=mock_model,
        profile=profile,
    )

    # 验证图可编译
    assert graph is not None
    # 验证节点存在
    nodes = graph.get_graph().nodes
    assert "decompose" in nodes
    assert "finalize" in nodes


def test_v2_section_summary_normalizes_citation_ids():
    from conflux.graph_v2 import _parse_section_summary

    parsed = _parse_section_summary(
        "正文引用[1]。\n---summary---\nClaim: 声明。[1]\n[1] 本地规范证据"
    )

    assert parsed["citation_refs"] == ["[1]"]
    assert parsed["key_claims"] == ["声明。[1]"]


def test_v2_citation_map_filters_noise_and_caps_same_source():
    from conflux.graph_v2 import _build_citation_map
    from conflux.source_status import EvidenceItem, SourceResult

    same_source = [
        EvidenceItem(
            claim=(f"Evidence statement {index} " * 8).strip(),
            source="Web",
            paper_id="arxiv:2405.13966",
            url="https://arxiv.org/html/2405.13966",
        )
        for index in range(4)
    ]
    claims = [
        EvidenceItem(
            claim="Ingestion action: summary_only - Relevance score: 0.810 - Reading level: deep " * 2,
            source="Web",
        ),
        EvidenceItem(
            claim="Learn more. Press Enter to search. Advanced search. " * 3,
            source="Web",
            url="https://arxiv.org/abs/2511.07127",
        ),
        *same_source,
        EvidenceItem(
            claim="Independent evidence about agent memory and context management. " * 3,
            source="Web",
            paper_id="arxiv:2501.00001",
            url="https://arxiv.org/pdf/2501.00001v1",
        ),
    ]
    raw = SourceResult(
        source="Web",
        status="success",
        content="usable",
        claims=claims,
        evidence_class="preprint",
    ).to_tool_text()

    citation_map = _build_citation_map("", raw)

    assert len(citation_map) == 2
    assert sum("2405.13966" in item for item in citation_map.values()) == 1
    assert "补充证据" in citation_map["[1]"]
    assert all("Ingestion action" not in item for item in citation_map.values())
    assert all("Press Enter to search" not in item for item in citation_map.values())


def test_v2_section_generation_uses_compact_citation_context():
    from conflux.graph_v2 import _generate_section

    class CapturingModel:
        prompt = ""

        def invoke(self, messages):
            self.prompt = messages[-1].content
            return SimpleNamespace(
                content="正文结论。[1]\n---summary---\nclaim: 可验证声明。[1]",
                usage_metadata={},
                response_metadata={},
            )

    model = CapturingModel()
    citation_map = {
        f"[{index}]": ("ReAct agent architecture evidence " * 30) + "（来源：Web https://example.test）"
        for index in range(1, 13)
    }

    result = _generate_section(
        {"id": "sq-1", "question": "ReAct agent architecture"},
        "agent design",
        "RAW_RAG_PAYLOAD " * 2000,
        "RAW_WEB_PAYLOAD " * 2000,
        citation_map,
        model,
    )

    assert "RAW_RAG_PAYLOAD" not in model.prompt
    assert "RAW_WEB_PAYLOAD" not in model.prompt
    assert '"[10]"' in model.prompt
    assert '"[11]"' not in model.prompt
    assert result.key_claims == ["可验证声明。[1]"]


def test_v2_factcheck_does_not_inherit_section_citations():
    from conflux.graph_v2 import factcheck_v2_node

    state = {
        "query": "研究问题",
        "_run_id": "claim-citation-run",
        "_run_status": "completed",
        "_report_available": True,
        "_report_markdown": "## 直接回答\n\n回答。\n\n## 可信度说明\n\n待核验。\n",
        "_citation_map": {"[1]": "外部证据"},
        "_section_results": [{
            "sub_question_id": "sq-1",
            "title": "章节",
            "body": "章节正文。[1]",
            "key_claims": ["没有声明级引用的结论。"],
            "citation_refs": ["[1]"],
            "finish_reason": "complete",
        }],
        "_audit_metrics": {"sections_completed": 1, "sections_failed": 0},
    }

    result = factcheck_v2_node(state, model=None)

    assert result["_factcheck_status"] == "failed"
    assert result["_factcheck_findings"]["verified_claims"] == 0
    assert result["_factcheck_findings"]["citation_refs_used"] == 0


def test_v2_finalize_removes_duplicate_credibility_heading():
    from conflux.graph_v2 import finalize_node

    result = finalize_node({
        "query": "研究问题",
        "_core_question": "研究问题",
        "_direct_answer": "直接回答。",
        "_credibility_text": "## 可信度说明\n\n## 可信度说明\n\n确定性结果。",
        "_started_at": 0,
    })

    assert result["_report_markdown"].count("## 可信度说明") == 1


def test_v2_failed_section_marks_run_partial_and_limits_factcheck_scope():
    import time

    from conflux.graph_v2 import V2State, audit_node, factcheck_v2_node

    now = time.time()
    state = {
        "query": "研究问题",
        "_run_id": "partial-run",
        "_started_at": now,
        "_deadline_at": now,
        "_report_markdown": "# 研究问题\n\n## 直接回答\n\n已有回答。[1]\n\n## 可信度说明\n\n部分证据。\n",
        "_report_available": True,
        "_citation_map": {"[1]": "外部证据"},
        "_rag_status": "success",
        "_rag_count": 1,
        "_web_status": "empty",
        "_web_count": 0,
        "_section_results": [
            {
                "sub_question_id": "ok",
                "title": "已完成问题",
                "body": "已有回答。[1]",
                "key_claims": ["已有回答。[1]"],
                "citation_refs": ["[1]"],
                "allowed_refs": ["[1]"],  # 生成时该节被分配了 [1]
                "finish_reason": "complete",
                "elapsed_ms": 1200,
                "usage": {"total_tokens": 80},
            },
            {
                "sub_question_id": "failed",
                "title": "未完成问题",
                "body": "本节因生成超时或失败未能完成。",
                "finish_reason": "failed",
                "elapsed_ms": 204000,
                "error": "TimeoutError: deadline",
            },
        ],
    }

    state.update(audit_node(state, model=None))
    state.update(factcheck_v2_node(state, model=None))

    assert state["_run_status"] == "partial"
    assert state["_delivery_status"] == "limited"
    assert state["_audit_metrics"]["sections_failed"] == 1
    assert state["_audit_metrics"]["section_runs"][1]["error"] == "TimeoutError: deadline"
    assert state["_factcheck_status"] == "passed"
    assert "仅核验已生成的声明" in state["_verified_answer"]
    assert "不代表整份报告完整通过" in state["_verified_answer"]
    assert state["_run_summary"]["delivery_status"] == "limited"
    assert "_delivery_status" in V2State.__annotations__
    assert "_delivery_assessment" in V2State.__annotations__


def test_deep_profile_allows_six_large_section_calls():
    from conflux.research_modes import resolve_research_profile

    profile = resolve_research_profile("deep")

    assert profile.token_budget == 320000


def test_query_command_prints_v2_artifact_paths(monkeypatch, tmp_path, capsys):
    import conflux.__main__ as cli
    import conflux.report as report

    profile = SimpleNamespace(
        timeout_seconds=60,
        commit_reserve_seconds=5,
        depth="quick",
        candidate_limit=3,
    )
    artifacts = SimpleNamespace(
        markdown_path=tmp_path / "report.md",
        html_path=tmp_path / "report.html",
        evidence_json_path=tmp_path / "report.evidence.json",
        raw_sources_path=tmp_path / "report.sources.md",
        deep_evidence_json_path=None,
        audit_markdown_path=tmp_path / "report.audit.md",
    )
    final_state = {
        "_report_markdown": "# Answer",
        "_report_available": True,
        "_run_status": "completed",
        "_confidence": "high",
    }

    monkeypatch.setattr(cli, "load_config", lambda: {"research": {}})
    monkeypatch.setattr(cli, "resolve_research_profile", lambda depth: profile)
    monkeypatch.setattr(cli, "validate_runtime_credentials", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "create_vector_store", lambda: object())
    monkeypatch.setattr(cli, "HybridRetriever", lambda store: object())
    monkeypatch.setattr(
        cli,
        "create_research_models",
        lambda *args, **kwargs: (
            {name: object() for name in ("analyst", "planner", "synthesizer", "verifier", "reranker")},
            {},
        ),
    )
    monkeypatch.setattr(cli, "set_model", lambda model: None)
    monkeypatch.setattr(cli, "QueryRewriteProvider", lambda model: object())
    monkeypatch.setattr(cli, "SemanticReranker", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_rag_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_web_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_checkpointer", lambda backend: SimpleNamespace(backend=backend))
    monkeypatch.setattr(cli, "create_sub_agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_v2_research_graph", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "_new_v2_state", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_phase2_graph", lambda *args, **kwargs: (final_state, []))
    monkeypatch.setattr(report, "write_v2_report_artifacts", lambda *args, **kwargs: artifacts)

    result = cli.query_command("test query", output_dir=str(tmp_path), run_id="test-run")

    output = capsys.readouterr().out
    assert f"Report Markdown: {artifacts.markdown_path.resolve()}" in output
    assert f"Report HTML: {artifacts.html_path.resolve()}" in output
    assert result["_report_artifacts"]["markdown_path"] == str(artifacts.markdown_path.resolve())


def test_system_prompt_has_final_marker():
    """验证 System Prompt 包含 ```final 标记"""
    from conflux.agent import SYSTEM_PROMPT, FINAL_MARKER
    assert FINAL_MARKER in SYSTEM_PROMPT


def test_golden_dataset_phase1_size():
    """Phase 1 Golden Dataset 至少包含 30 条样例。"""
    import yaml

    dataset = yaml.safe_load(Path("data/golden_dataset.yaml").read_text(encoding="utf-8"))
    assert len(dataset) >= 30


def test_prompt_files_exist():
    """验证架构文档要求的关键 prompt 文件已落地。"""
    required = [
        "prompts/agents/rag_agent.system.yaml",
        "prompts/agents/web_agent.system.yaml",
        "prompts/agents/model_agent.system.yaml",
        "prompts/agents/factcheck_agent.system.yaml",
        "prompts/evaluation/judge.system.yaml",
        "prompts/generation/report_composer.yaml",
        "prompts/routing/intent_classifier.yaml",
    ]
    for path in required:
        assert Path(path).exists()


def test_sub_agent_loads_prompt_file():
    """子 Agent 使用 prompts/ 中的 system prompt。"""
    from unittest.mock import MagicMock

    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool as tool_decorator

    from conflux.agent import create_sub_agent

    @tool_decorator
    def dummy_rag(query: str) -> str:
        """Search dummy local documents."""
        return query

    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.bind_tools.return_value = mock_model

    agent = create_sub_agent("rag", mock_model, dummy_rag)

    assert "本地知识库检索 Agent" in agent.system_prompt


def test_validate_runtime_credentials_reports_missing_keys(monkeypatch):
    """真实运行前能给出清晰凭据缺失说明。"""
    from conflux.model_factory import validate_runtime_credentials

    for name in [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CONFLUX_MODELS__REASONING__API_KEY",
        "CONFLUX_MODELS__CHEAP__API_KEY",
        "CONFLUX_EMBEDDING__API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)

    problems = validate_runtime_credentials()

    assert any("models." in problem for problem in problems)
    assert any("embedding" in problem for problem in problems)


def test_validate_embedding_credentials_reports_missing_key(monkeypatch):
    """索引命令只需要 embedding key，也应给出清晰缺失说明。"""
    from conflux.model_factory import validate_embedding_credentials

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CONFLUX_EMBEDDING__API_KEY", raising=False)

    problems = validate_embedding_credentials()

    assert any("embedding" in problem for problem in problems)


def test_default_config_is_api_first():
    """默认配置必须是 API-first，不要求本地模型。"""
    from conflux.config import get

    assert get("models", "reasoning", "provider") == "openai_compatible"
    assert get("models", "cheap", "provider") == "openai_compatible"
    assert get("embedding", "provider") == "openai_compatible"
