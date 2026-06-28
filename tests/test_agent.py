"""基本烟雾测试 — 验证所有模块可导入，Graph 可编译"""

import sys
from pathlib import Path

# 确保项目在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """验证核心模块可导入"""
    from conflux.config import load, get
    from conflux.model_factory import create_chat_model, create_embedding_model
    from conflux.rag import chunk_documents, create_vector_store, HybridRetriever
    from conflux.tools import create_rag_tool, search_web
    from conflux.agent import ResearchAgent, SYSTEM_PROMPT
    from conflux.graph import create_graph, AgentState
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


def test_graph_compiles():
    """验证 LangGraph 可编译（不需要真实 API key）"""
    from unittest.mock import MagicMock
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool as tool_decorator

    from conflux.agent import ResearchAgent
    from conflux.graph import create_graph

    @tool_decorator
    def dummy_search(query: str) -> str:
        """Search dummy test data."""
        return f"dummy result for: {query}"

    # 用 mock 模型
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.bind_tools.return_value = mock_model

    agent = ResearchAgent(mock_model, [dummy_search])
    graph = create_graph(agent)

    # 验证图可编译
    assert graph is not None
    # 验证节点存在
    nodes = graph.get_graph().nodes
    assert "agent" in nodes
    assert "finalize" in nodes


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

    assert any("models.reasoning" in problem for problem in problems)
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
